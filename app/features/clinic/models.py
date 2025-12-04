# Clinic Management Feature

from typing import Optional
from beanie import Document, Indexed
from app.shared.models import TimestampMixin


class Clinic(Document, TimestampMixin):
    """Clinic document model for managing clinic settings and branding."""
    
    name: str
    owner_id: Optional[str] = None  # User ID who owns/created this clinic
    address: Optional[str] = ""
    logo_url: Optional[str] = ""
    primary_color: str = "#0ea5e9"  # Default primary color
    # Keep old field name for backward compatibility
    color_theme: Optional[str] = None
    
    # Contact information
    phone: Optional[str] = ""
    email: Optional[str] = ""
    
    # Location for Google Maps
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    class Settings:
        name = "clinics"
        use_state_management = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Advanced Health Clinic",
                "owner_id": "user_123",
                "address": "123 Medical Ave",
                "logo_url": "",
                "primary_color": "#0ea5e9",
                "phone": "+1 (555) 123-4567",
                "email": "contact@clinic.com",
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        }
