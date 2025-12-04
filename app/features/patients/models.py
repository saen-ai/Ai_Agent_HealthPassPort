# Patient Management Feature - Models

from typing import Optional, List
from datetime import date, datetime
from beanie import Document, Indexed
from pydantic import EmailStr, Field
from app.shared.models import TimestampMixin


class Medication(dict):
    """Medication structure for patient records."""
    name: str
    dosage: str
    frequency: str


class Patient(Document, TimestampMixin):
    """Patient document model for storing patient health records."""
    
    # Unique patient identifier (e.g., P00001)
    patient_id: Indexed(str, unique=True)
    
    # Clinic association - patient belongs to one clinic
    clinic_id: Indexed(str)
    
    # Authentication credentials
    email: Indexed(EmailStr)
    password_hash: str
    
    # Personal information
    name: str
    date_of_birth: date
    gender: str  # Male, Female, Other
    phone: Optional[str] = None
    address: Optional[str] = None
    avatar_url: Optional[str] = None
    
    # Health information
    conditions: List[str] = Field(default_factory=list)
    medications: List[dict] = Field(default_factory=list)  # [{name, dosage, frequency}]
    allergies: List[str] = Field(default_factory=list)
    
    # Status
    is_active: bool = True
    
    # Notification preferences
    notifications_enabled: bool = True  # Enable/disable browser notifications
    
    class Settings:
        name = "patients"
        use_state_management = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "P00001",
                "clinic_id": "clinic_123",
                "email": "patient@email.com",
                "name": "Sarah Johnson",
                "date_of_birth": "1990-05-15",
                "gender": "Female",
                "phone": "+1234567890",
                "address": "123 Main St",
                "conditions": ["Type 2 Diabetes", "Hypertension"],
                "medications": [
                    {"name": "Metformin", "dosage": "500mg", "frequency": "Twice daily"}
                ],
                "allergies": ["Penicillin"],
                "is_active": True
            }
        }


class PatientPasswordReset(Document, TimestampMixin):
    """Patient password reset token document model."""
    
    patient_id: str
    email: EmailStr
    token: Indexed(str, unique=True)
    expires_at: datetime
    used: bool = False
    
    class Settings:
        name = "patient_password_resets"
        use_state_management = True
