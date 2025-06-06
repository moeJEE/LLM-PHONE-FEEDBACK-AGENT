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


class QuestionType(str, Enum):
    """Enumeration of question types"""
    OPEN_ENDED = "open_ended"
    NUMERIC = "numeric"
    YES_NO = "yes_no"
    MULTIPLE_CHOICE = "multiple_choice"


class SurveyStatus(str, Enum):
    """Enumeration of survey statuses"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class VoiceType(str, Enum):
    """Enumeration of voice types"""
    NEUTRAL_FEMALE = "neutral_female"
    NEUTRAL_MALE = "neutral_male"
    PROFESSIONAL_FEMALE = "professional_female"
    PROFESSIONAL_MALE = "professional_male"
    FRIENDLY_FEMALE = "friendly_female"
    FRIENDLY_MALE = "friendly_male"


class VoiceSpeed(str, Enum):
    """Enumeration of voice speeds"""
    SLOW = "slow"
    NORMAL = "normal"
    FAST = "fast"


class QuestionLogic(BaseModel):
    """Question logic for branching surveys"""
    condition: str  # e.g., "1-2", "3", "4-5", "yes", "no", or an option value
    next_question_id: str


class SurveyQuestion(BaseModel):
    """Survey question model"""
    id: str
    text: str
    voice_prompt: str
    question_type: QuestionType
    required: bool = True
    options: List[str] = []
    follow_up_logic: Dict[str, str] = {}  # condition -> question_id


class SurveyBase(BaseModel):
    """Base model for surveys with common fields"""
    title: str
    description: str
    intro_message: str
    outro_message: str
    voice_type: VoiceType = VoiceType.NEUTRAL_FEMALE
    voice_speed: VoiceSpeed = VoiceSpeed.NORMAL
    max_duration: int = 10  # minutes
    max_retries: int = 3
    call_during_business_hours: bool = True
    avoid_weekends: bool = True
    respect_timezone: bool = True
    status: SurveyStatus = SurveyStatus.DRAFT
    questions: List[SurveyQuestion]


class SurveyCreate(SurveyBase):
    """Model for creating a new survey"""
    pass


class SurveyDB(SurveyBase):
    """Survey model as stored in the database"""
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()))
    owner_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            ObjectId: str
        }


class SurveyUpdate(BaseModel):
    """Model for updating an existing survey"""
    title: Optional[str] = None
    description: Optional[str] = None
    intro_message: Optional[str] = None
    outro_message: Optional[str] = None
    voice_type: Optional[VoiceType] = None
    voice_speed: Optional[VoiceSpeed] = None
    max_duration: Optional[int] = None
    max_retries: Optional[int] = None
    call_during_business_hours: Optional[bool] = None
    avoid_weekends: Optional[bool] = None
    respect_timezone: Optional[bool] = None
    status: Optional[SurveyStatus] = None
    questions: Optional[List[SurveyQuestion]] = None


class SurveyResponse(SurveyBase):
    """Survey model for API responses"""
    id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
    
    
class SurveyResult(BaseModel):
    """Survey result model"""
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()))
    survey_id: str
    call_id: str
    contact_phone_number: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    completed: bool = False
    responses: Dict[str, Any] = {}  # question_id -> response
    sentiment_scores: Dict[str, float] = {}  # question_id -> sentiment score
    overall_sentiment: Optional[float] = None
    
    class Config:
        json_encoders = {
            ObjectId: str
        }