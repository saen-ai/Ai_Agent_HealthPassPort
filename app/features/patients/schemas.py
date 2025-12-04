# Patient Management Feature - Schemas

from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, EmailStr, Field


# ============== Medication Schema ==============

class MedicationSchema(BaseModel):
    """Schema for medication information."""
    name: str
    dosage: str
    frequency: str


# ============== Create Patient ==============

class CreatePatientRequest(BaseModel):
    """Request schema for creating a new patient."""
    email: EmailStr
    password: str = Field(..., min_length=6, description="Initial password for patient")
    name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date
    gender: str = Field(..., pattern=r'^(Male|Female|Other)$')
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    conditions: List[str] = Field(default_factory=list)
    medications: List[MedicationSchema] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)


# ============== Update Patient ==============

class UpdatePatientRequest(BaseModel):
    """Request schema for updating patient information."""
    email: Optional[EmailStr] = None
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, pattern=r'^(Male|Female|Other)$')
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    conditions: Optional[List[str]] = None
    medications: Optional[List[MedicationSchema]] = None
    allergies: Optional[List[str]] = None
    is_active: Optional[bool] = None


# ============== Patient Response ==============

class PatientResponse(BaseModel):
    """Response schema for patient data."""
    id: str
    patient_id: str
    clinic_id: str
    email: str
    name: str
    date_of_birth: date
    gender: str
    phone: Optional[str] = None
    address: Optional[str] = None
    avatar_url: Optional[str] = None
    conditions: List[str] = []
    medications: List[dict] = []
    allergies: List[str] = []
    is_active: bool
    notifications_enabled: bool = True
    created_at: datetime
    updated_at: datetime


class PatientListResponse(BaseModel):
    """Response schema for list of patients."""
    patients: List[PatientResponse]
    total: int


# ============== Patient Authentication ==============

class PatientLoginRequest(BaseModel):
    """Request schema for patient login."""
    patient_id: str = Field(..., description="Patient ID (e.g., P00001)")
    password: str = Field(..., min_length=1)


class ClinicInfo(BaseModel):
    """Clinic information for patient portal."""
    id: str
    name: str
    logo_url: Optional[str] = None
    primary_color: str = "#0ea5e9"
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class PatientLoginResponse(BaseModel):
    """Response schema for patient login."""
    access_token: str
    token_type: str = "bearer"
    patient: PatientResponse
    clinic: ClinicInfo


class PatientMeResponse(BaseModel):
    """Response schema for current patient info."""
    patient: PatientResponse
    clinic: ClinicInfo


# ============== Create Patient Response ==============

class CreatePatientResponse(BaseModel):
    """Response schema for newly created patient."""
    patient: PatientResponse
    generated_patient_id: str
    message: str = "Patient created successfully"


# ============== Patient Password Reset ==============

class PatientForgotPasswordRequest(BaseModel):
    """Request schema for patient forgot password."""
    patient_id: str = Field(..., description="Patient ID (e.g., P00001)")
    email: EmailStr = Field(..., description="Patient's email address")


class PatientResetPasswordRequest(BaseModel):
    """Request schema for patient password reset."""
    token: str = Field(..., description="Password reset token from email")
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")


# ============== Notification Settings ==============

class NotificationSettingsRequest(BaseModel):
    """Notification settings request schema."""
    notifications_enabled: bool = Field(..., description="Enable or disable browser notifications")


# ============== Change Password ==============

class ChangePasswordRequest(BaseModel):
    """Request schema for changing patient password."""
    current_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(..., min_length=6, description="New password (min 6 characters)")


# ============== Message Response ==============

class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
