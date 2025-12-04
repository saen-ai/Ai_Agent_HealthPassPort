# Messages Feature - Models

from typing import Optional, List, Literal
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field
from app.shared.models import TimestampMixin


class Conversation(Document, TimestampMixin):
    """
    Conversation document model.
    Represents a chat thread between a doctor (user) and a patient.
    Each patient has one conversation per clinic.
    """
    
    # Clinic this conversation belongs to
    clinic_id: Indexed(str)
    
    # Doctor (User) in this conversation
    user_id: Indexed(str)
    
    # Patient in this conversation
    patient_id: Indexed(str)
    
    # Last message preview for conversation list
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    last_message_sender: Optional[Literal["doctor", "patient"]] = None
    
    # Unread counts for each party
    doctor_unread_count: int = 0
    patient_unread_count: int = 0
    
    # Status
    is_active: bool = True
    
    class Settings:
        name = "conversations"
        use_state_management = True
        indexes = [
            # Compound index for finding conversation between doctor and patient
            [("clinic_id", 1), ("patient_id", 1)],
            # Index for listing conversations by user
            [("user_id", 1), ("last_message_at", -1)],
            # Index for listing conversations by patient
            [("patient_id", 1), ("last_message_at", -1)],
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "clinic_id": "clinic_123",
                "user_id": "user_456",
                "patient_id": "P00001",
                "last_message": "Thank you, doctor!",
                "last_message_at": "2024-01-15T10:30:00Z",
                "last_message_sender": "patient",
                "doctor_unread_count": 1,
                "patient_unread_count": 0,
            }
        }


class PushSubscription(Document, TimestampMixin):
    """
    Push notification subscription document model.
    Stores Web Push API subscriptions for users and patients.
    """
    
    # User or patient identifier
    user_id: Optional[str] = None  # For doctors (user_id)
    patient_id: Optional[str] = None  # For patients
    
    # Subscription type
    subscription_type: Literal["doctor", "patient"]
    
    # Push subscription data
    endpoint: str
    p256dh: str  # Public key
    auth: str  # Auth secret
    
    # Status
    is_active: bool = True
    
    class Settings:
        name = "push_subscriptions"
        use_state_management = True
        indexes = [
            [("user_id", 1)],
            [("patient_id", 1)],
            [("endpoint", 1)],
        ]


class Message(Document, TimestampMixin):
    """
    Message document model.
    Represents a single message in a conversation.
    """
    
    # Reference to the conversation
    conversation_id: Indexed(str)
    
    # Sender information
    sender_type: Literal["doctor", "patient"]
    sender_id: str  # user_id for doctor, patient_id for patient
    sender_name: str  # Display name of sender
    
    # Message content
    content: str
    
    # Attachment (optional - for future file sharing)
    attachment_url: Optional[str] = None
    attachment_type: Optional[str] = None  # "image", "document", etc.
    
    # Read status
    read_at: Optional[datetime] = None
    
    # Message status
    is_deleted: bool = False
    
    class Settings:
        name = "messages"
        use_state_management = True
        indexes = [
            # Index for fetching messages in a conversation (sorted by time)
            [("conversation_id", 1), ("created_at", 1)],
            # Index for unread messages
            [("conversation_id", 1), ("read_at", 1)],
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "conv_789",
                "sender_type": "doctor",
                "sender_id": "user_456",
                "sender_name": "Dr. Sarah Anderson",
                "content": "Your lab results look good!",
                "read_at": None,
            }
        }
