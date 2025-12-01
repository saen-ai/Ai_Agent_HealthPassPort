from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import Optional


class TimestampMixin:
    """Mixin for adding timestamp fields to documents."""
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()


class BaseDocument(Document, TimestampMixin):
    """Base document class with timestamps."""
    
    class Settings:
        use_state_management = True
