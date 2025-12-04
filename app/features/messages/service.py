# Messages Feature - Service

from typing import Optional, List, Literal, Tuple
from datetime import datetime
from bson import ObjectId
from app.features.messages.models import Conversation, Message
from app.features.messages.schemas import (
    MessageCreate,
    MessageResponse,
    ConversationResponse,
)
from app.features.patients.models import Patient
from app.features.auth.models import User
from app.core.logging import logger
from app.shared.exceptions import NotFoundException, BadRequestException


class MessageService:
    """Service class for messaging operations."""
    
    # Reference to Socket.IO server (set during app startup)
    sio = None
    
    @classmethod
    def set_socketio(cls, sio):
        """Set the Socket.IO server instance."""
        cls.sio = sio
    
    @staticmethod
    async def get_or_create_conversation(
        clinic_id: str,
        user_id: str,
        patient_id: str
    ) -> Conversation:
        """
        Get existing conversation or create a new one.
        
        Args:
            clinic_id: Clinic ID
            user_id: Doctor's user ID
            patient_id: Patient ID (e.g., P00001)
            
        Returns:
            Conversation document
        """
        # Try to find existing conversation
        conversation = await Conversation.find_one(
            Conversation.clinic_id == clinic_id,
            Conversation.patient_id == patient_id
        )
        
        if conversation:
            # Update user_id if different (in case of reassignment)
            if conversation.user_id != user_id:
                conversation.user_id = user_id
                await conversation.save()
            return conversation
        
        # Create new conversation
        conversation = Conversation(
            clinic_id=clinic_id,
            user_id=user_id,
            patient_id=patient_id,
        )
        await conversation.insert()
        
        logger.info(f"Created new conversation for patient {patient_id} in clinic {clinic_id}")
        return conversation
    
    @staticmethod
    async def get_conversation_by_id(
        conversation_id: str,
        user_id: Optional[str] = None,
        patient_id: Optional[str] = None
    ) -> Conversation:
        """
        Get conversation by ID with access check.
        
        Args:
            conversation_id: Conversation ID
            user_id: Optional user ID for access check
            patient_id: Optional patient ID for access check
            
        Returns:
            Conversation document
            
        Raises:
            NotFoundException: If conversation not found or access denied
        """
        try:
            conversation = await Conversation.get(ObjectId(conversation_id))
        except Exception:
            raise NotFoundException("Conversation not found")
        
        if not conversation:
            raise NotFoundException("Conversation not found")
        
        # Access check - must be participant
        if user_id and conversation.user_id != user_id:
            # Check if user belongs to the same clinic
            user = await User.get(ObjectId(user_id))
            if not user or user.clinic_id != conversation.clinic_id:
                raise NotFoundException("Conversation not found")
        
        if patient_id and conversation.patient_id != patient_id:
            raise NotFoundException("Conversation not found")
        
        return conversation
    
    @staticmethod
    async def get_conversations_for_doctor(
        clinic_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[ConversationResponse], int]:
        """
        Get all conversations for a doctor.
        
        Args:
            clinic_id: Clinic ID
            user_id: Doctor's user ID
            limit: Max number of conversations
            offset: Pagination offset
            
        Returns:
            Tuple of (conversations list, total count)
        """
        # Get conversations for clinic, sorted by last message
        query = Conversation.find(
            Conversation.clinic_id == clinic_id,
            Conversation.is_active == True
        ).sort([("last_message_at", -1), ("created_at", -1)])
        
        total = await query.count()
        conversations = await query.skip(offset).limit(limit).to_list()
        
        # Enrich with patient info
        result = []
        for conv in conversations:
            # Get patient info
            patient = await Patient.find_one(Patient.patient_id == conv.patient_id)
            
            result.append(ConversationResponse(
                id=str(conv.id),
                clinic_id=conv.clinic_id,
                user_id=conv.user_id,
                patient_id=conv.patient_id,
                patient_name=patient.name if patient else "Unknown Patient",
                patient_avatar=patient.avatar_url if patient else None,
                last_message=conv.last_message,
                last_message_at=conv.last_message_at,
                last_message_sender=conv.last_message_sender,
                unread_count=conv.doctor_unread_count,
                is_active=conv.is_active,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
            ))
        
        return result, total
    
    @staticmethod
    async def get_conversations_for_patient(
        patient_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[ConversationResponse], int]:
        """
        Get all conversations for a patient.
        
        Args:
            patient_id: Patient ID
            limit: Max number of conversations
            offset: Pagination offset
            
        Returns:
            Tuple of (conversations list, total count)
        """
        query = Conversation.find(
            Conversation.patient_id == patient_id,
            Conversation.is_active == True
        ).sort([("last_message_at", -1), ("created_at", -1)])
        
        total = await query.count()
        conversations = await query.skip(offset).limit(limit).to_list()
        
        # Enrich with doctor info
        result = []
        for conv in conversations:
            # Get doctor info
            try:
                doctor = await User.get(ObjectId(conv.user_id))
            except Exception:
                doctor = None
            
            result.append(ConversationResponse(
                id=str(conv.id),
                clinic_id=conv.clinic_id,
                user_id=conv.user_id,
                patient_id=conv.patient_id,
                doctor_name=doctor.name if doctor else "Your Doctor",
                doctor_avatar=doctor.profile_picture_url if doctor else None,
                last_message=conv.last_message,
                last_message_at=conv.last_message_at,
                last_message_sender=conv.last_message_sender,
                unread_count=conv.patient_unread_count,
                is_active=conv.is_active,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
            ))
        
        return result, total
    
    @staticmethod
    async def get_messages(
        conversation_id: str,
        limit: int = 50,
        before: Optional[datetime] = None
    ) -> Tuple[List[MessageResponse], int, bool]:
        """
        Get messages in a conversation.
        
        Args:
            conversation_id: Conversation ID
            limit: Max number of messages
            before: Get messages before this timestamp (for pagination)
            
        Returns:
            Tuple of (messages list, total count, has_more)
        """
        # Build query using Beanie syntax
        query = Message.find(
            Message.conversation_id == conversation_id,
            Message.is_deleted == False
        )
        
        # Add before filter if provided
        if before:
            query = query.find(Message.created_at < before)
        
        # Get total count
        total = await query.count()
        
        # Get messages sorted by newest first for pagination, then reverse for display
        messages = await query.sort(
            [("created_at", -1)]
        ).limit(limit + 1).to_list()
        
        has_more = len(messages) > limit
        messages = messages[:limit]
        
        # Reverse to get chronological order (oldest first)
        messages.reverse()
        
        result = [
            MessageResponse(
                id=str(msg.id),
                conversation_id=msg.conversation_id,
                sender_type=msg.sender_type,
                sender_id=msg.sender_id,
                sender_name=msg.sender_name,
                content=msg.content,
                attachment_url=msg.attachment_url,
                attachment_type=msg.attachment_type,
                read_at=msg.read_at,
                created_at=msg.created_at,
                updated_at=msg.updated_at,
            )
            for msg in messages
        ]
        
        logger.info(f"Fetched {len(result)} messages for conversation {conversation_id} (total: {total})")
        
        return result, total, has_more
    
    @staticmethod
    async def send_message(
        conversation_id: str,
        sender_type: Literal["doctor", "patient"],
        sender_id: str,
        sender_name: str,
        content: str,
        attachment_url: Optional[str] = None,
        attachment_type: Optional[str] = None
    ) -> MessageResponse:
        """
        Send a message in a conversation.
        
        Args:
            conversation_id: Conversation ID
            sender_type: "doctor" or "patient"
            sender_id: Sender's ID
            sender_name: Sender's display name
            content: Message content
            attachment_url: Optional attachment URL
            attachment_type: Optional attachment type
            
        Returns:
            Created message response
        """
        # Verify conversation exists
        try:
            conversation = await Conversation.get(ObjectId(conversation_id))
        except Exception:
            raise NotFoundException("Conversation not found")
        
        if not conversation:
            raise NotFoundException("Conversation not found")
        
        # Create message
        message = Message(
            conversation_id=conversation_id,
            sender_type=sender_type,
            sender_id=sender_id,
            sender_name=sender_name,
            content=content,
            attachment_url=attachment_url,
            attachment_type=attachment_type,
        )
        await message.insert()
        
        logger.info(f"Message saved to MongoDB: id={message.id}, conversation_id={conversation_id}, content={content[:50]}...")
        
        # Update conversation
        conversation.last_message = content[:100] if len(content) > 100 else content
        conversation.last_message_at = message.created_at
        conversation.last_message_sender = sender_type
        
        # Increment unread count for the other party
        if sender_type == "doctor":
            conversation.patient_unread_count += 1
        else:
            conversation.doctor_unread_count += 1
        
        await conversation.save()
        
        logger.info(f"Message sent in conversation {conversation_id} by {sender_type}")
        
        # Create response
        response = MessageResponse(
            id=str(message.id),
            conversation_id=message.conversation_id,
            sender_type=message.sender_type,
            sender_id=message.sender_id,
            sender_name=message.sender_name,
            content=message.content,
            attachment_url=message.attachment_url,
            attachment_type=message.attachment_type,
            read_at=message.read_at,
            created_at=message.created_at,
            updated_at=message.updated_at,
        )
        
        # Broadcast via Socket.IO if available
        if MessageService.sio:
            await MessageService.sio.emit(
                "new_message",
                {
                    "message": response.model_dump(mode="json"),
                    "conversation_id": conversation_id
                },
                room=f"conversation_{conversation_id}"
            )
        
        return response
    
    @staticmethod
    async def mark_messages_as_read(
        conversation_id: str,
        reader_type: Literal["doctor", "patient"]
    ) -> int:
        """
        Mark all unread messages in a conversation as read.
        
        Args:
            conversation_id: Conversation ID
            reader_type: Who is reading ("doctor" or "patient")
            
        Returns:
            Number of messages marked as read
        """
        # Get conversation
        try:
            conversation = await Conversation.get(ObjectId(conversation_id))
        except Exception:
            raise NotFoundException("Conversation not found")
        
        if not conversation:
            raise NotFoundException("Conversation not found")
        
        # Mark messages from the OTHER party as read
        other_type = "patient" if reader_type == "doctor" else "doctor"
        
        now = datetime.utcnow()
        result = await Message.find(
            Message.conversation_id == conversation_id,
            Message.sender_type == other_type,
            Message.read_at == None,
            Message.is_deleted == False
        ).update_many({"$set": {"read_at": now}})
        
        # Reset unread count for the reader
        if reader_type == "doctor":
            conversation.doctor_unread_count = 0
        else:
            conversation.patient_unread_count = 0
        
        await conversation.save()
        
        count = result.modified_count if result else 0
        
        logger.info(f"Marked {count} messages as read in conversation {conversation_id}")
        
        # Broadcast read status via Socket.IO
        if MessageService.sio and count > 0:
            await MessageService.sio.emit(
                "messages_read",
                {
                    "conversation_id": conversation_id,
                    "read_by": reader_type,
                    "read_at": now.isoformat()
                },
                room=f"conversation_{conversation_id}"
            )
        
        return count
    
    @staticmethod
    async def get_unread_count_for_doctor(clinic_id: str) -> int:
        """Get total unread message count for a doctor across all conversations."""
        result = await Conversation.find(
            Conversation.clinic_id == clinic_id,
            Conversation.is_active == True
        ).sum("doctor_unread_count")
        
        return result or 0
    
    @staticmethod
    async def get_unread_count_for_patient(patient_id: str) -> int:
        """Get total unread message count for a patient across all conversations."""
        result = await Conversation.find(
            Conversation.patient_id == patient_id,
            Conversation.is_active == True
        ).sum("patient_unread_count")
        
        return result or 0
