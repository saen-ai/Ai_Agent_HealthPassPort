from beanie import Document, Indexed
from pydantic import EmailStr, Field
from typing import Optional, Literal
from datetime import datetime
from app.shared.models import TimestampMixin


class User(Document, TimestampMixin):
    """User document model."""
    
    email: Indexed(EmailStr, unique=True)
    password_hash: str
    name: str
    phone: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    
    # Role and clinic association
    role: str = "admin"  # For Phase 1, all users are admin
    clinic_id: Optional[str] = None  # Will be populated after clinic creation
    
    class Settings:
        name = "users"
        use_state_management = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "admin@example.com",
                "name": "John Doe",
                "phone": "+1234567890",
            }
        }


class PasswordReset(Document, TimestampMixin):
    """Password reset token document model."""
    
    user_id: str
    email: EmailStr
    token: Indexed(str, unique=True)
    expires_at: datetime
    used: bool = False
    
    class Settings:
        name = "password_resets"
        use_state_management = True


class EmailVerification(Document, TimestampMixin):
    """Email verification OTP document model."""
    
    email: Indexed(EmailStr)
    otp_code: str
    expires_at: datetime
    used: bool = False
    purpose: Literal["signup", "login"] = "signup"
    
    class Settings:
        name = "email_verifications"
        use_state_management = True
