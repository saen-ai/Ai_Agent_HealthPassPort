from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from typing import Optional
from app.config import settings
from app.core.logging import logger


class Database:
    """MongoDB database connection manager."""
    
    client: Optional[AsyncIOMotorClient] = None
    
    @classmethod
    async def connect_db(cls):
        """Connect to MongoDB and initialize Beanie."""
        cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
        
        # Import all document models here
        from app.features.auth.models import User, PasswordReset, EmailVerification
        from app.features.clinic.models import Clinic
        
        # Initialize Beanie with document models
        await init_beanie(
            database=cls.client[settings.DATABASE_NAME],
            document_models=[
                User,
                PasswordReset,
                EmailVerification,
                Clinic,
                # Add more models as features are implemented
            ]
        )
        
        logger.info(f"Connected to MongoDB database: {settings.DATABASE_NAME}")
    
    @classmethod
    async def close_db(cls):
        """Close MongoDB connection."""
        if cls.client:
            cls.client.close()
            logger.info("Closed MongoDB connection")


# Dependency for getting database connection
async def get_database():
    """Dependency for database access."""
    return Database.client[settings.DATABASE_NAME]
