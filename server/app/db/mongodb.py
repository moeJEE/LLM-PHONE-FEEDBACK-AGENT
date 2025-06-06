from motor.motor_asyncio import AsyncIOMotorClient
from ..core.config import get_settings

settings = get_settings()

class MongoDB:
    client: AsyncIOMotorClient = None
    
    @classmethod
    async def connect(cls):
        """Connect to MongoDB"""
        cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
        cls.database = cls.client[settings.MONGODB_DB_NAME]
        
        # Use proper logging instead of print
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Connected to MongoDB at {settings.MONGODB_URL}")
    
    @classmethod
    async def close(cls):
        """Close MongoDB connection"""
        if cls.client:
            cls.client.close()
            
            # Use proper logging instead of print
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Closed connection with MongoDB")
    
    @classmethod
    def get_db(cls):
        return cls.client[settings.MONGODB_DB_NAME]
    
    @classmethod
    def get_collection(cls, collection_name: str):
        return cls.get_db()[collection_name]