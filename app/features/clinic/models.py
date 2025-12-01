# Clinic Management Feature
# TODO: Implement clinic management functionality

from beanie import Document
from app.shared.models import TimestampMixin


class Clinic(Document, TimestampMixin):
    """Clinic document model - To be implemented."""
    
    name: str
    address: str = ""
    logo_url: str = ""
    color_theme: str = "#4F46E5"
    
    class Settings:
        name = "clinics"
