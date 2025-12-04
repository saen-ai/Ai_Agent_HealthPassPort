from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime


# Request Schemas
class SignupRequest(BaseModel):
    """Signup request schema."""
    
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    clinic_name: str = Field(..., min_length=2, max_length=200)
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class LoginRequest(BaseModel):
    """Login request schema."""
    
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    """Forgot password request schema."""
    
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password request schema."""
    
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class ChangePasswordRequest(BaseModel):
    """Change password request schema."""
    
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class UpdateProfileRequest(BaseModel):
    """Update profile request schema."""
    
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = None
    specialization: Optional[str] = Field(None, max_length=200)


class NotificationSettingsRequest(BaseModel):
    """Notification settings request schema."""
    
    notifications_enabled: bool = Field(..., description="Enable or disable browser notifications")


class SendSignupOtpRequest(BaseModel):
    """Send signup OTP request schema."""
    
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=100)
    clinic_name: str = Field(..., min_length=2, max_length=200)
    password: str = Field(..., min_length=8, max_length=100)
    phone: Optional[str] = None
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class VerifySignupOtpRequest(BaseModel):
    """Verify signup OTP request schema."""
    
    email: EmailStr
    otp_code: str = Field(..., min_length=4, max_length=4)
    name: str = Field(..., min_length=2, max_length=100)
    clinic_name: str = Field(..., min_length=2, max_length=200)
    password: str = Field(..., min_length=8, max_length=100)
    phone: Optional[str] = None
    
    @field_validator('otp_code')
    @classmethod
    def validate_otp(cls, v: str) -> str:
        # Strip whitespace
        v = v.strip()
        if not v.isdigit():
            raise ValueError('OTP code must be numeric')
        if len(v) != 4:
            raise ValueError('OTP code must be exactly 4 digits')
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class SendLoginOtpRequest(BaseModel):
    """Send login OTP request schema."""
    
    email: EmailStr


class VerifyLoginOtpRequest(BaseModel):
    """Verify login OTP request schema."""
    
    email: EmailStr
    otp_code: str = Field(..., min_length=4, max_length=4)
    
    @field_validator('otp_code')
    @classmethod
    def validate_otp(cls, v: str) -> str:
        # Strip whitespace
        v = v.strip()
        if not v.isdigit():
            raise ValueError('OTP code must be numeric')
        if len(v) != 4:
            raise ValueError('OTP code must be exactly 4 digits')
        return v


# Response Schemas
class UserResponse(BaseModel):
    """User response schema."""
    
    id: str
    email: EmailStr
    name: str
    phone: Optional[str] = None
    specialization: Optional[str] = None
    profile_picture_url: Optional[str] = None
    role: str
    clinic_id: Optional[str] = None
    is_active: bool
    is_verified: bool
    notifications_enabled: bool = True
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token response schema."""
    
    access_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    """Login response schema."""
    
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class SignupResponse(BaseModel):
    """Signup response schema."""
    
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    clinic_id: Optional[str] = None


class MessageResponse(BaseModel):
    """Generic message response."""
    
    message: str
