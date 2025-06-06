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


class CallDirection(str, Enum):
    """Enumeration of call directions"""
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CallStatus(str, Enum):
    """Enumeration of call statuses"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in-progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CallPriority(str, Enum):
    """Enumeration of call priorities"""
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class CallEvent(BaseModel):
    """Call event model for tracking call history"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: str  # e.g., "scheduled", "started", "paused", "resumed", "completed", "failed"
    description: str
    metadata: Dict[str, Any] = {}


class CallBase(BaseModel):
    """Base model for calls with common fields"""
    phone_number: str
    survey_id: str
    direction: CallDirection = CallDirection.OUTBOUND
    scheduled_time: Optional[datetime] = None
    priority: CallPriority = CallPriority.NORMAL
    notes: Optional[str] = None
    contact_name: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    twilio_call_sid: Optional[str] = None


class CallCreate(CallBase):
    """Model for creating a new call"""
    pass


class CallDB(CallBase):
    """Call model as stored in the database"""
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()))
    owner_id: str
    status: CallStatus = CallStatus.SCHEDULED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    events: List[CallEvent] = []
    survey_result_id: Optional[str] = None
    metadata: Dict[str, Any] = {}
    
    class Config:
        json_encoders = {
            ObjectId: str
        }


class CallUpdate(BaseModel):
    """Model for updating an existing call"""
    phone_number: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    priority: Optional[CallPriority] = None
    notes: Optional[str] = None
    contact_name: Optional[str] = None
    max_retries: Optional[int] = None
    status: Optional[CallStatus] = None
    metadata: Optional[Dict[str, Any]] = None


class CallResponse(CallBase):
    """Call model for API responses"""
    id: str
    owner_id: str
    status: CallStatus
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    events: List[CallEvent] = []
    survey_result_id: Optional[str] = None
    metadata: Dict[str, Any] = {}


class CallLogQuery(BaseModel):
    """Query parameters for filtering call logs"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[List[CallStatus]] = None
    direction: Optional[CallDirection] = None
    survey_id: Optional[str] = None
    phone_number: Optional[str] = None


class CallStats(BaseModel):
    """Statistics for calls"""
    total_calls: int = 0
    scheduled_calls: int = 0
    in_progress_calls: int = 0
    completed_calls: int = 0
    failed_calls: int = 0
    cancelled_calls: int = 0
    average_duration_seconds: Optional[float] = None
    total_duration_seconds: Optional[float] = None
    completion_rate: Optional[float] = None