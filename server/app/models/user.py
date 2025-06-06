from pydantic import BaseModel, Field, EmailStr
from typing import List, Dict, Any, Optional
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


class UserStatus(str, Enum):
    """Enumeration of user statuses"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class UserRole(str, Enum):
    """Enumeration of user roles"""
    ADMIN = "admin"
    MANAGER = "manager"
    AGENT = "agent"
    VIEWER = "viewer"


class UserBase(BaseModel):
    """Base model for users with common fields"""
    clerk_id: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: UserRole = UserRole.AGENT
    status: UserStatus = UserStatus.ACTIVE
    profile_completed: bool = False
    phone_number: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    company_name: Optional[str] = None
    avatar_url: Optional[str] = None
    metadata: Dict[str, Any] = {}


class UserDB(UserBase):
    """User model as stored in the database"""
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            ObjectId: str
        }


class UserCreate(UserBase):
    """Model for creating a new user"""
    pass


class UserUpdate(BaseModel):
    """Model for updating an existing user"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    profile_completed: Optional[bool] = None
    phone_number: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    company_name: Optional[str] = None
    avatar_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class UserResponse(UserBase):
    """User model for API responses"""
    id: str
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None


class UserActivity(BaseModel):
    """User activity model for tracking user actions"""
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()))
    user_id: str
    activity_type: str  # e.g., "login", "survey_created", "call_started"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = {}
    
    class Config:
        json_encoders = {
            ObjectId: str
        }