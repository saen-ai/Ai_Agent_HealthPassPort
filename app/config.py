"""Application configuration settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database - shared with main backend
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "health_passport"
    
    # OpenAI
    OPENAI_API_KEY: str
    
    # Application
    APP_NAME: str = "AI Health Passport"
    API_V1_PREFIX: str = "/api/v1"
    PORT: int = 8001  # Separate from main backend (8000)
    
    # CORS - allow main backend and frontends
    BACKEND_CORS_ORIGINS: str = '["http://localhost:3000", "http://localhost:3001", "http://localhost:8000"]'
    
    # File storage
    UPLOAD_DIR: str = "/tmp/lab_reports"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore extra fields from shared .env
    )
    
    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from JSON string."""
        try:
            return json.loads(self.BACKEND_CORS_ORIGINS)
        except:
            return ["http://localhost:3000"]


settings = Settings()

