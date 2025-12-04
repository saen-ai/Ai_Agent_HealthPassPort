# Notes Feature - Models

from typing import Optional
from beanie import Document, Indexed
from app.shared.models import TimestampMixin


class Note(Document, TimestampMixin):
    """
    Note document model.
    Represents a clinical note for a patient, created by a doctor.
    Notes can be private (clinic only) or shared with the patient.
    """
    
    # Clinic this note belongs to
    clinic_id: Indexed(str)
    
    # Patient this note is about
    patient_id: Indexed(str)  # e.g., P00001
    
    # Doctor who created the note
    user_id: str  # References User._id
    provider_name: str  # Stored for display purposes
    
    # Note content
    title: str
    content: str
    
    # Visibility: True = shared with patient, False = private to clinic
    is_shared: bool = True
    
    # Status
    is_deleted: bool = False
    
    class Settings:
        name = "notes"
        use_state_management = True
        indexes = [
            # Index for fetching notes by patient
            [("clinic_id", 1), ("patient_id", 1), ("is_deleted", 1)],
            # Index for sorting by creation date
            [("patient_id", 1), ("created_at", -1)],
            # Index for shared notes (patient view)
            [("patient_id", 1), ("is_shared", 1), ("is_deleted", 1)],
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "clinic_id": "clinic_123",
                "patient_id": "P00001",
                "user_id": "user_456",
                "provider_name": "Dr. Sarah Anderson",
                "title": "Follow-up Consultation",
                "content": "Patient reports improved energy levels. Continue current medication.",
                "is_shared": True,
                "is_deleted": False,
            }
        }
