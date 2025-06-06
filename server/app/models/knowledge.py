from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from enum import Enum
from datetime import datetime
from bson import ObjectId


class PyObjectId(str):
    """Custom type for handling MongoDB ObjectIDs"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)


class DocumentStatus(str, Enum):
    """Enumeration of document processing statuses"""
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class DocumentType(str, Enum):
    """Enumeration of document types"""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    CSV = "csv"
    XLSX = "xlsx"
    HTML = "html"
    MARKDOWN = "markdown"
    OTHER = "other"


class DocumentBase(BaseModel):
    """Base model for knowledge base documents"""
    name: str
    description: Optional[str] = None
    document_type: DocumentType
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class DocumentCreate(DocumentBase):
    """Model for creating a new document"""
    content: Optional[str] = None  # Text content if directly provided
    file_path: Optional[str] = None  # Path to uploaded file
    url: Optional[str] = None  # URL if document is fetched from web


class DocumentDB(DocumentBase):
    """Document model as stored in the database"""
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()))
    owner_id: str
    status: DocumentStatus = DocumentStatus.PROCESSING
    content: Optional[str] = None  # Extracted text content
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    file_size: Optional[int] = None  # Size in bytes
    page_count: Optional[int] = None
    error_message: Optional[str] = None
    embeddings_count: Optional[int] = None  # Number of chunks/embeddings created
    vector_collection_name: Optional[str] = None  # Name of collection in vector DB
    
    class Config:
        json_encoders = {
            ObjectId: str
        }


class DocumentUpdate(BaseModel):
    """Model for updating an existing document"""
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    status: Optional[DocumentStatus] = None


class DocumentResponse(DocumentBase):
    """Document model for API responses"""
    id: str
    owner_id: str
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    error_message: Optional[str] = None
    embeddings_count: Optional[int] = None


class TextChunk(BaseModel):
    """Model for text chunks created from documents"""
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()))
    document_id: str
    content: str
    chunk_index: int
    metadata: Dict[str, Any] = {}
    embedding: Optional[List[float]] = None
    
    class Config:
        json_encoders = {
            ObjectId: str
        }


class SearchQuery(BaseModel):
    """Model for searching knowledge base"""
    query: str
    filters: Optional[Dict[str, Any]] = None
    top_k: int = 5


class SearchResult(BaseModel):
    """Model for search results"""
    id: str
    document_id: str
    document_name: str
    content: str
    score: float
    metadata: Dict[str, Any] = {}