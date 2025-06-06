from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, List
from pathlib import Path
from dotenv import load_dotenv
from pydantic import field_validator

# Charger automatiquement server/.env au démarrage
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env", override=True)

class Settings(BaseSettings):
    # Server Configuration
    API_HOST: str
    API_PORT: int
    DEBUG: bool
    ENVIRONMENT: str

    # WhatsApp Testing
    WHATSAPP_SIMULATION_MODE: bool

    # Security
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Database
    MONGODB_URL: str
    MONGODB_DB_NAME: str

    # Vector Database
    QDRANT_URL: Optional[str] = None
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: Optional[str] = None
    VECTOR_DB_TYPE: str

    # LLM Provider
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    LLM_PROVIDER: str
    EMBEDDING_MODEL: str

    # Twilio
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_PHONE_NUMBER: str
    TWILIO_WEBHOOK_URL: str
    TWILIO_STATUS_CALLBACK_URL: str
    TWILIO_RECORDING_CALLBACK_URL: str

    # Twilio WhatsApp Settings
    TWILIO_WHATSAPP_FROM: str
    TWILIO_WHATSAPP_CONTENT_SID: str

    # Nexmo/Vonage WhatsApp Settings
    NEXMO_API_KEY: str
    NEXMO_API_SECRET: str
    NEXMO_WHATSAPP_FROM: str
    NEXMO_WEBHOOK_URL: str
    NEXMO_STATUS_WEBHOOK_URL: str

    # Speech Services
    DEEPGRAM_API_KEY: Optional[str] = None
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    STT_PROVIDER: str

    # Text to Speech
    TTS_PROVIDER: str
    ELEVENLABS_API_KEY: Optional[str] = None

    # CORS
    CORS_ORIGINS: List[str]

    # Clerk configuration
    CLERK_INSTANCE_ID: str
    CLERK_SECRET_KEY: str

    @field_validator("OPENAI_API_KEY")
    @classmethod
    def validate_openai_api_key(cls, v: str) -> str:
        """Validate and clean OpenAI API key"""
        if not v:
            return v
        
        # Clean the value (remove quotes, whitespace)
        cleaned = v.strip().strip('"').strip("'")
        
        # Validate format (starts with sk- and has reasonable length)
        if not cleaned.startswith("sk-") or len(cleaned) < 20:
            raise ValueError("OPENAI_API_KEY must start with 'sk-' and be a valid OpenAI API key")
        
        return cleaned

@lru_cache()
def get_settings():
    """Get application settings with validation"""
    s = Settings()

    # Clean and validate API key if provided
    if s.OPENAI_API_KEY:
        s.OPENAI_API_KEY = s.OPENAI_API_KEY.strip()

    return s
