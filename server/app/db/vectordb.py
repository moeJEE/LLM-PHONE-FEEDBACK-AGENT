from ..core.config import get_settings
import numpy as np
from typing import List, Dict, Any, Optional

settings = get_settings()

class VectorDB:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorDB, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance
    
    def initialize(self):
        self.db_type = settings.VECTOR_DB_TYPE
        
        if self.db_type == "qdrant":
            from qdrant_client import QdrantClient
            try:
                qdrant_client = QdrantClient(url=settings.QDRANT_URL)
                
                # Use proper logging instead of print
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Connected to Qdrant at {settings.QDRANT_URL}")
                return qdrant_client
            except Exception as e:
                raise ConnectionError(f"Failed to connect to Qdrant: {e}")
        
        elif self.db_type == "pinecone":
            import pinecone
            try:
                pinecone.init(
                    api_key=settings.PINECONE_API_KEY,
                    environment=settings.PINECONE_ENVIRONMENT
                )
                index = pinecone.Index("embeddings")
                
                # Use proper logging instead of print
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Connected to Pinecone in {settings.PINECONE_ENVIRONMENT} environment")
                return index
            except Exception as e:
                raise ConnectionError(f"Failed to connect to Pinecone: {e}")
        
        elif self.db_type == "chroma":
            import chromadb
            try:
                chroma_client = chromadb.Client()
                
                # Use proper logging instead of print
                import logging
                logger = logging.getLogger(__name__)
                logger.info("Connected to local ChromaDB")
                return chroma_client
            except Exception as e:
                raise ConnectionError(f"Failed to connect to ChromaDB: {e}")
        
        else:
            raise ValueError(f"Unsupported vector database type: {self.db_type}")
    
    def create_collection(self, collection_name: str, dimension: int = 1536):
        """Create a new collection in the vector database"""
        if self.db_type == "qdrant":
            from qdrant_client.http import models
            self.client.recreate_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=dimension,
                    distance=models.Distance.COSINE
                )
            )
        elif self.db_type == "pinecone":
            # Check if index exists, create it if it doesn't
            if collection_name not in self.client.list_indexes():
                self.client.create_index(
                    name=collection_name,
                    dimension=dimension,
                    metric="cosine"
                )
        elif self.db_type == "chroma":
            self.client.create_collection(name=collection_name)
    
    def add_texts(
        self,
        collection_name: str,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ):
        """Add texts and their embeddings to the vector database"""
        if metadatas is None:
            metadatas = [{} for _ in texts]
        
        if ids is None:
            import uuid
            ids = [str(uuid.uuid4()) for _ in texts]
        
        if self.db_type == "qdrant":
            from qdrant_client.http import models
            self.client.upsert(
                collection_name=collection_name,
                points=[
                    models.PointStruct(
                        id=id,
                        vector=embedding,
                        payload={"text": text, **metadata}
                    )
                    for id, text, embedding, metadata in zip(ids, texts, embeddings, metadatas)
                ]
            )
        elif self.db_type == "pinecone":
            index = self.client.Index(collection_name)
            index.upsert(
                vectors=zip(
                    ids,
                    embeddings,
                    [{"text": text, **metadata} for text, metadata in zip(texts, metadatas)]
                )
            )
        elif self.db_type == "chroma":
            collection = self.client.get_collection(name=collection_name)
            collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
    
    def similarity_search(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar documents based on embedding"""
        if self.db_type == "qdrant":
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=top_k
            )
            return [
                {
                    "id": result.id,
                    "text": result.payload.get("text", ""),
                    "metadata": {k: v for k, v in result.payload.items() if k != "text"},
                    "score": result.score
                } 
                for result in results
            ]
        elif self.db_type == "pinecone":
            index = self.client.Index(collection_name)
            results = index.query(
                query_embedding,
                top_k=top_k,
                include_metadata=True
            )
            return [
                {
                    "id": match.id,
                    "text": match.metadata.get("text", ""),
                    "metadata": {k: v for k, v in match.metadata.items() if k != "text"},
                    "score": match.score
                } 
                for match in results.matches
            ]
        elif self.db_type == "chroma":
            collection = self.client.get_collection(name=collection_name)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            return [
                {
                    "id": id,
                    "text": document,
                    "metadata": metadata,
                    "score": float(distance)
                } 
                for id, document, metadata, distance in zip(
                    results["ids"][0],
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0]
                )
            ]