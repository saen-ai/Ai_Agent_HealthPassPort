from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime


class BaseResponse(BaseModel):
    """Base response model."""
    
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Error response model."""
    
    success: bool = False
    message: str
    detail: Optional[Dict[str, Any]] = None


class TimestampSchema(BaseModel):
    """Schema for timestamp fields."""
    
    created_at: datetime
    updated_at: datetime
