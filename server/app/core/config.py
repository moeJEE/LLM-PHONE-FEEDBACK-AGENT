from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, List
from pathlib import Path
from dotenv import load_dotenv
from pydantic import field_validator

# Charger automatiquement server/.env au démarrage
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env", override=True)

class Settings(BaseSettings):
    # Serveur
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # WhatsApp Testing
    WHATSAPP_SIMULATION_MODE: bool = False

    # Sécurité
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # MongoDB
    MONGODB_URL: str
    MONGODB_DB_NAME: str = "phone_feedback_system"

    # Vector DB
    QDRANT_URL: Optional[str] = None
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: Optional[str] = None
    VECTOR_DB_TYPE: str = "qdrant"  # qdrant, pinecone, ou chroma

    # LLM Provider
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "openai"
    EMBEDDING_MODEL: str = "text-embedding-ada-002"

    # Twilio
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_PHONE_NUMBER: str
    TWILIO_WEBHOOK_URL: str
    TWILIO_STATUS_CALLBACK_URL: str
    TWILIO_RECORDING_CALLBACK_URL: str

    # Twilio WhatsApp Settings
    TWILIO_WHATSAPP_FROM: str = "whatsapp:+14155238886"
    TWILIO_WHATSAPP_CONTENT_SID: str = "HXb5b62575e6e4ff6129ad7c8efe1f983e"

    # Nexmo/Vonage WhatsApp Settings
    NEXMO_API_KEY: str
    NEXMO_API_SECRET: str
    NEXMO_WHATSAPP_FROM: str = "14157386102"
    NEXMO_WEBHOOK_URL: str
    NEXMO_STATUS_WEBHOOK_URL: str

    # Speech Services
    DEEPGRAM_API_KEY: Optional[str] = None
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    STT_PROVIDER: str = "deepgram"  # deepgram ou google

    # Text to Speech
    TTS_PROVIDER: str = "google"  # google ou elevenlabs
    ELEVENLABS_API_KEY: Optional[str] = None

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Clerk configuration
    CLERK_INSTANCE_ID: str
    CLERK_SECRET_KEY: str

    @field_validator("OPENAI_API_KEY")
    @classmethod
    def validate_openai_api_key(cls, v: str) -> str:
        """Validate and clean OpenAI API key"""
        if not v or v in ["YOUR_OPENAI_API_KEY", "your_openai_api_key_here"]:
            raise ValueError("OPENAI_API_KEY is required and must be set to a valid API key")
        
        # Clean the API key
        cleaned = v.strip().strip('"').strip("'")
        
        # Validate format (starts with sk- and has reasonable length)
        if not cleaned.startswith("sk-") or len(cleaned) < 20:
            raise ValueError("OPENAI_API_KEY must start with 'sk-' and be a valid OpenAI API key")
        
        # Remove debug print statement
        # Only log in debug mode with proper logging
        if cls.DEBUG:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Cleaned API KEY: {repr(cleaned)}")
        
        return cleaned

@lru_cache()
def get_settings():
    """Get application settings with validation"""
    s = Settings()

    # Clean and validate API key if provided
    if s.OPENAI_API_KEY:
        s.OPENAI_API_KEY = s.OPENAI_API_KEY.strip()
        
        # Only log in debug mode with proper logging
        if s.DEBUG:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"OpenAI API key configured: {s.OPENAI_API_KEY[:8]}...")
            logger.debug(f"WhatsApp simulation mode: {s.WHATSAPP_SIMULATION_MODE}")

    return s
