from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import shutil
from pathlib import Path
from bson import ObjectId

from ..core.security import get_current_user, ClerkUser
from ..core.logging import get_logger
from ..db.mongodb import MongoDB
from ..db.vectordb import VectorDB
from ..models.knowledge import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentDB,
    DocumentStatus,
    DocumentType,
    SearchQuery,
    SearchResult
)
from ..services.document_processor.document_loader import DocumentLoader
from ..services.document_processor.text_chunker import TextChunker
from ..services.document_processor.embedding_generator import EmbeddingGenerator
from ..core.config import get_settings

logger = get_logger("api.knowledge")
router = APIRouter()

# Helper function to convert MongoDB document to Pydantic model
def convert_document_doc(doc):
    if not doc:
        return None
    
    doc["id"] = str(doc.pop("_id"))
    return DocumentResponse(**doc)

# Create upload directory if it doesn't exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Background task to process uploaded document
async def process_document(document_id: str, file_path: str, owner_id: str):
    try:
        documents_collection = MongoDB.get_collection("documents")
        
        # Load document
        logger.info(f"Processing document: {file_path}")
        doc_data = DocumentLoader.load_file(file_path)
        
        # Extract metadata
        metadata = doc_data["metadata"]
        content = doc_data["content"]
        
        # Update document with content and metadata
        update_data = {
            "content": content,
            "file_size": metadata.get("size_bytes"),
            "metadata": {**metadata},
            "updated_at": datetime.utcnow()
        }
        
        # Chunk the document
        chunks = TextChunker.chunk_document({
            "content": content,
            "metadata": metadata
        })
        
        logger.info(f"Created {len(chunks)} chunks for document {document_id}")
        
        # Generate embeddings
        embedding_generator = EmbeddingGenerator()
        chunk_texts = [chunk["content"] for chunk in chunks]
        embeddings = embedding_generator.generate_embeddings(chunk_texts)
        
        # Create vector collection name
        vector_collection_name = f"doc_{document_id}"
        
        # Initialize vector database
        vector_db = VectorDB()
        vector_db.create_collection(vector_collection_name)
        
        # Add chunks to vector database
        chunk_metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = {
                "document_id": document_id,
                "chunk_index": i,
                **chunk["metadata"]
            }
            chunk_metadatas.append(chunk_metadata)
        
        vector_db.add_texts(
            collection_name=vector_collection_name,
            texts=chunk_texts,
            embeddings=embeddings,
            metadatas=chunk_metadatas
        )
        
        # Update document status
        update_data.update({
            "status": DocumentStatus.PROCESSED.value,
            "processed_at": datetime.utcnow(),
            "embeddings_count": len(chunks),
            "vector_collection_name": vector_collection_name
        })
        
        await documents_collection.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": update_data}
        )
        
        logger.info(f"Document processed successfully: {document_id}")
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}", exc_info=True)
        
        # Update document with error
        await documents_collection.update_one(
            {"_id": ObjectId(document_id)},
            {
                "$set": {
                    "status": DocumentStatus.FAILED.value,
                    "error_message": str(e),
                    "updated_at": datetime.utcnow()
                }
            }
        )

# Endpoints
@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    name: str = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    current_user: ClerkUser = Depends(get_current_user)
):
    """Upload a document to the knowledge base"""
    # Determine document type from file extension
    file_extension = os.path.splitext(file.filename)[1].lower()[1:]  # Remove the dot
    
    try:
        doc_type = DocumentType(file_extension)
    except ValueError:
        doc_type = DocumentType.OTHER
    
    # Use original filename if name not provided
    document_name = name or file.filename
    
    # Parse tags
    tag_list = []
    if tags:
        tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
    
    # Create document record
    document_db = DocumentDB(
        name=document_name,
        description=description,
        document_type=doc_type,
        tags=tag_list,
        owner_id=current_user.id,
        status=DocumentStatus.PROCESSING,
        metadata={
            "original_filename": file.filename,
        }
    )
    
    # Insert into database
    documents_collection = MongoDB.get_collection("documents")
    result = await documents_collection.insert_one(document_db.dict(by_alias=True))
    document_id = str(result.inserted_id)
    
    # Save file
    file_path = UPLOAD_DIR / f"{document_id}_{file.filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Process document in background
    background_tasks.add_task(
        process_document, 
        document_id, 
        str(file_path), 
        current_user.id
    )
    
    # Get created document
    created_document = await documents_collection.find_one({"_id": result.inserted_id})
    
    # Log the upload with a non-conflicting key
    logger.info(f"Document uploaded with ID: {document_id}", 
                extra={"user_id": current_user.id, "uploaded_filename": file.filename})
    
    return convert_document_doc(created_document)


@router.get("/", response_model=List[DocumentResponse])
async def get_documents(
    status: Optional[str] = Query(None, description="Filter by document status"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    skip: int = Query(0, ge=0, description="Number of documents to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of documents to return"),
    current_user: ClerkUser = Depends(get_current_user)
):
    """Get all documents in the knowledge base"""
    settings = get_settings()
    
    documents_collection = MongoDB.get_collection("documents")
    
    # Build query
    query = {}
    
    # In production, filter by owner_id. In debug mode, show all documents
    if not settings.DEBUG:
        query["owner_id"] = current_user.id
    
    # Add status filter
    if status:
        try:
            doc_status = DocumentStatus(status)
            query["status"] = doc_status.value
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    
    # Add document type filter
    if document_type:
        try:
            doc_type = DocumentType(document_type)
            query["document_type"] = doc_type.value
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid document type: {document_type}"
            )
    
    # Add tag filter
    if tag:
        query["tags"] = tag
    
    # Execute query
    cursor = documents_collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
    documents = await cursor.to_list(length=limit)
    
    return [convert_document_doc(doc) for doc in documents]

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: ClerkUser = Depends(get_current_user)
):
    """Get a specific document by ID"""
    settings = get_settings()
    documents_collection = MongoDB.get_collection("documents")
    
    # Check if valid ObjectId
    if not ObjectId.is_valid(document_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format"
        )
    
    # Build query
    query = {"_id": ObjectId(document_id)}
    
    # In production, filter by owner_id. In debug mode, allow access to all documents
    if not settings.DEBUG:
        query["owner_id"] = current_user.id
    
    # Find document
    document = await documents_collection.find_one(query)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return convert_document_doc(document)

@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    document_update: DocumentUpdate,
    current_user: ClerkUser = Depends(get_current_user)
):
    """Update a document"""
    settings = get_settings()
    documents_collection = MongoDB.get_collection("documents")
    
    # Check if valid ObjectId
    if not ObjectId.is_valid(document_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format"
        )
    
    # Build query
    query = {"_id": ObjectId(document_id)}
    
    # In production, filter by owner_id. In debug mode, allow access to all documents
    if not settings.DEBUG:
        query["owner_id"] = current_user.id
    
    # Find document
    existing_document = await documents_collection.find_one(query)
    
    if not existing_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Remove None values from update
    update_data = {k: v for k, v in document_update.dict().items() if v is not None}
    
    # Always update the updated_at timestamp
    update_data["updated_at"] = datetime.utcnow()
    
    # Update document
    await documents_collection.update_one(
        {"_id": ObjectId(document_id)},
        {"$set": update_data}
    )
    
    # Get updated document
    updated_document = await documents_collection.find_one({"_id": ObjectId(document_id)})
    
    logger.info(f"Document updated with ID: {document_id}", extra={"user_id": current_user.id})
    
    return convert_document_doc(updated_document)

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    current_user: ClerkUser = Depends(get_current_user)
):
    """Delete a document"""
    settings = get_settings()
    documents_collection = MongoDB.get_collection("documents")
    
    # Check if valid ObjectId
    if not ObjectId.is_valid(document_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format"
        )
    
    # Build query
    query = {"_id": ObjectId(document_id)}
    
    # In production, filter by owner_id. In debug mode, allow access to all documents
    if not settings.DEBUG:
        query["owner_id"] = current_user.id
    
    # Find document
    existing_document = await documents_collection.find_one(query)
    
    if not existing_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # If document has vectors, delete them
    vector_collection_name = existing_document.get("vector_collection_name")
    if vector_collection_name:
        try:
            vector_db = VectorDB()
            # Note: This would need to be implemented in the VectorDB class
            # vector_db.delete_collection(vector_collection_name)
        except Exception as e:
            logger.error(f"Error deleting vector collection: {str(e)}", exc_info=True)
    
    # Delete document file if it exists
    file_path = None
    for file in UPLOAD_DIR.glob(f"{document_id}_*"):
        file_path = file
        break
    
    if file_path and file_path.exists():
        file_path.unlink()
    
    # Delete document
    await documents_collection.delete_one({"_id": ObjectId(document_id)})
    
    logger.info(f"Document deleted with ID: {document_id}", extra={"user_id": current_user.id})

@router.post("/search", response_model=List[SearchResult])
async def search_knowledge_base(
    query: SearchQuery,
    current_user: ClerkUser = Depends(get_current_user)
):
    """Search the knowledge base"""
    documents_collection = MongoDB.get_collection("documents")
    
    # Generate embedding for query
    embedding_generator = EmbeddingGenerator()
    query_embedding = embedding_generator.generate_embeddings([query.query])[0]
    
    # Get user's documents
    user_docs = await documents_collection.find({
        "owner_id": current_user.id,
        "status": DocumentStatus.PROCESSED.value
    }).to_list(length=100)
    
    if not user_docs:
        return []
    
    # Initialize results
    all_results = []
    
    # For each document, search its vector collection
    vector_db = VectorDB()
    
    for doc in user_docs:
        vector_collection_name = doc.get("vector_collection_name")
        if not vector_collection_name:
            continue
        
        try:
            # Search vector DB
            results = vector_db.similarity_search(
                collection_name=vector_collection_name,
                query_embedding=query_embedding,
                top_k=query.top_k
            )
            
            # Add document info to results
            for result in results:
                all_results.append(
                    SearchResult(
                        id=result["id"],
                        document_id=str(doc["_id"]),
                        document_name=doc["name"],
                        content=result["text"],
                        score=result["score"],
                        metadata=result["metadata"]
                    )
                )
        except Exception as e:
            logger.error(f"Error searching vector collection: {str(e)}", exc_info=True)
    
    # Sort by score
    all_results.sort(key=lambda x: x.score, reverse=True)
    
    # Return top results
    return all_results[:query.top_k]