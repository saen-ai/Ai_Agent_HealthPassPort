# Clinic schemas
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ClinicResponse(BaseModel):
    """Response schema for clinic data."""
    id: str
    name: str
    owner_id: str
    address: Optional[str] = ""
    logo_url: Optional[str] = ""
    primary_color: str = "#0ea5e9"
    phone: Optional[str] = ""
    email: Optional[str] = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class UpdateClinicRequest(BaseModel):
    """Request schema for updating clinic settings."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    logo_url: Optional[str] = None
    primary_color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
