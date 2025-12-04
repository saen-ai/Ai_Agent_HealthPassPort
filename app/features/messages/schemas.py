# Messages Feature - Schemas

from typing import Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field


# ============== Message Schemas ==============

class MessageCreate(BaseModel):
    """Request schema for creating a new message."""
    content: str = Field(..., min_length=1, max_length=5000)
    attachment_url: Optional[str] = None
    attachment_type: Optional[str] = None


class MessageResponse(BaseModel):
    """Response schema for a message."""
    id: str
    conversation_id: str
    sender_type: Literal["doctor", "patient"]
    sender_id: str
    sender_name: str
    content: str
    attachment_url: Optional[str] = None
    attachment_type: Optional[str] = None
    read_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class MessageListResponse(BaseModel):
    """Response schema for list of messages."""
    messages: List[MessageResponse]
    total: int
    has_more: bool


# ============== Conversation Schemas ==============

class ConversationCreate(BaseModel):
    """Request schema for creating/starting a conversation."""
    patient_id: str = Field(..., description="Patient ID to start conversation with")


class ConversationResponse(BaseModel):
    """Response schema for a conversation."""
    id: str
    clinic_id: str
    user_id: str
    patient_id: str
    patient_name: Optional[str] = None  # Populated from patient data
    patient_avatar: Optional[str] = None  # Populated from patient data
    doctor_name: Optional[str] = None  # Populated from user data
    doctor_avatar: Optional[str] = None  # Populated from user data
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    last_message_sender: Optional[Literal["doctor", "patient"]] = None
    unread_count: int = 0  # Unread count for the requesting party
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    """Response schema for list of conversations."""
    conversations: List[ConversationResponse]
    total: int


# ============== Socket.IO Event Schemas ==============

class SocketMessageEvent(BaseModel):
    """Schema for new_message socket event."""
    message: MessageResponse
    conversation_id: str


class SocketTypingEvent(BaseModel):
    """Schema for typing socket event."""
    conversation_id: str
    user_type: Literal["doctor", "patient"]
    user_name: str
    is_typing: bool


class SocketReadEvent(BaseModel):
    """Schema for message_read socket event."""
    conversation_id: str
    message_ids: List[str]
    read_by: Literal["doctor", "patient"]
    read_at: datetime


# ============== Generic Response ==============

class MessageStatusResponse(BaseModel):
    """Generic status response."""
    message: str
    success: bool = True


# ============== Push Subscription Schemas ==============

class PushSubscriptionKeys(BaseModel):
    """Push subscription keys."""
    p256dh: str
    auth: str


class PushSubscriptionRequest(BaseModel):
    """Request schema for push subscription."""
    endpoint: str
    keys: PushSubscriptionKeys


class PushSubscriptionResponse(BaseModel):
    """Response schema for push subscription."""
    message: str
    success: bool = True
