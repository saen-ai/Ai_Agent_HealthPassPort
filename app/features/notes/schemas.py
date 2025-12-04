# Notes Feature - Schemas

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class NoteCreate(BaseModel):
    """Schema for creating a new note."""
    patient_id: str = Field(..., description="Patient ID (e.g., P00001)")
    title: str = Field(..., min_length=1, max_length=200, description="Note title")
    content: str = Field(..., min_length=1, description="Note content")
    is_shared: bool = Field(default=True, description="Whether the note is shared with the patient")
    
    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "P00001",
                "title": "Follow-up Consultation",
                "content": "Patient reports improved energy levels. Continue current medication.",
                "is_shared": True,
            }
        }


class NoteUpdate(BaseModel):
    """Schema for updating an existing note."""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Note title")
    content: Optional[str] = Field(None, min_length=1, description="Note content")
    is_shared: Optional[bool] = Field(None, description="Whether the note is shared with the patient")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Updated Title",
                "content": "Updated content",
                "is_shared": False,
            }
        }


class NoteResponse(BaseModel):
    """Schema for note response."""
    id: str
    clinic_id: str
    patient_id: str
    user_id: str
    provider_name: str
    title: str
    content: str
    is_shared: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "note_123",
                "clinic_id": "clinic_456",
                "patient_id": "P00001",
                "user_id": "user_789",
                "provider_name": "Dr. Sarah Anderson",
                "title": "Follow-up Consultation",
                "content": "Patient reports improved energy levels.",
                "is_shared": True,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z",
            }
        }


class NoteListResponse(BaseModel):
    """Schema for paginated list of notes."""
    notes: List[NoteResponse]
    total: int
    has_more: bool
