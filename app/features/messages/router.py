# Messages Feature - Router

from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime
from app.features.messages.schemas import (
    MessageCreate,
    MessageResponse,
    MessageListResponse,
    ConversationCreate,
    ConversationResponse,
    ConversationListResponse,
    MessageStatusResponse,
)
from app.features.messages.service import MessageService
from app.features.auth.dependencies import get_current_user
from app.features.patients.dependencies import get_current_patient
from app.features.auth.models import User
from app.features.patients.models import Patient
from app.core.logging import logger


router = APIRouter(prefix="/messages", tags=["Messages"])


# ============== Doctor Endpoints (Require User Auth) ==============

@router.get("/conversations", response_model=ConversationListResponse)
async def get_doctor_conversations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user)
):
    """
    Get all conversations for the current doctor.
    
    Requires doctor/admin authentication.
    """
    if not current_user.clinic_id:
        from app.shared.exceptions import BadRequestException
        raise BadRequestException("You must be associated with a clinic")
    
    conversations, total = await MessageService.get_conversations_for_doctor(
        clinic_id=current_user.clinic_id,
        user_id=str(current_user.id),
        limit=limit,
        offset=offset
    )
    
    return ConversationListResponse(conversations=conversations, total=total)


@router.post("/conversations", response_model=ConversationResponse)
async def create_or_get_conversation(
    request: ConversationCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create or get existing conversation with a patient.
    
    Requires doctor/admin authentication.
    """
    if not current_user.clinic_id:
        from app.shared.exceptions import BadRequestException
        raise BadRequestException("You must be associated with a clinic")
    
    # Verify patient exists in the clinic
    patient = await Patient.find_one(
        Patient.patient_id == request.patient_id,
        Patient.clinic_id == current_user.clinic_id
    )
    
    if not patient:
        from app.shared.exceptions import NotFoundException
        raise NotFoundException("Patient not found in your clinic")
    
    conversation = await MessageService.get_or_create_conversation(
        clinic_id=current_user.clinic_id,
        user_id=str(current_user.id),
        patient_id=request.patient_id
    )
    
    return ConversationResponse(
        id=str(conversation.id),
        clinic_id=conversation.clinic_id,
        user_id=conversation.user_id,
        patient_id=conversation.patient_id,
        patient_name=patient.name,
        patient_avatar=patient.avatar_url,
        last_message=conversation.last_message,
        last_message_at=conversation.last_message_at,
        last_message_sender=conversation.last_message_sender,
        unread_count=conversation.doctor_unread_count,
        is_active=conversation.is_active,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse)
async def get_conversation_messages(
    conversation_id: str,
    limit: int = Query(50, ge=1, le=100),
    before: Optional[datetime] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get messages in a conversation.
    
    Requires doctor/admin authentication.
    """
    # Verify access
    conversation = await MessageService.get_conversation_by_id(
        conversation_id=conversation_id,
        user_id=str(current_user.id)
    )
    
    messages, total, has_more = await MessageService.get_messages(
        conversation_id=conversation_id,
        limit=limit,
        before=before
    )
    
    return MessageListResponse(messages=messages, total=total, has_more=has_more)


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_message_as_doctor(
    conversation_id: str,
    request: MessageCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Send a message in a conversation.
    
    Requires doctor/admin authentication.
    """
    # Verify access
    conversation = await MessageService.get_conversation_by_id(
        conversation_id=conversation_id,
        user_id=str(current_user.id)
    )
    
    message = await MessageService.send_message(
        conversation_id=conversation_id,
        sender_type="doctor",
        sender_id=str(current_user.id),
        sender_name=current_user.name,
        content=request.content,
        attachment_url=request.attachment_url,
        attachment_type=request.attachment_type
    )
    
    return message


@router.post("/conversations/{conversation_id}/read", response_model=MessageStatusResponse)
async def mark_messages_read_as_doctor(
    conversation_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Mark all messages in a conversation as read.
    
    Requires doctor/admin authentication.
    """
    # Verify access
    conversation = await MessageService.get_conversation_by_id(
        conversation_id=conversation_id,
        user_id=str(current_user.id)
    )
    
    count = await MessageService.mark_messages_as_read(
        conversation_id=conversation_id,
        reader_type="doctor"
    )
    
    return MessageStatusResponse(message=f"Marked {count} messages as read")


@router.get("/unread-count")
async def get_doctor_unread_count(
    current_user: User = Depends(get_current_user)
):
    """
    Get total unread message count for the doctor.
    
    Requires doctor/admin authentication.
    """
    if not current_user.clinic_id:
        return {"unread_count": 0}
    
    count = await MessageService.get_unread_count_for_doctor(current_user.clinic_id)
    
    return {"unread_count": count}


# ============== Patient Endpoints (Require Patient Auth) ==============

@router.get("/patient/conversations", response_model=ConversationListResponse)
async def get_patient_conversations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_patient: Patient = Depends(get_current_patient)
):
    """
    Get all conversations for the current patient.
    
    Requires patient authentication.
    """
    conversations, total = await MessageService.get_conversations_for_patient(
        patient_id=current_patient.patient_id,
        limit=limit,
        offset=offset
    )
    
    return ConversationListResponse(conversations=conversations, total=total)


@router.get("/patient/conversations/{conversation_id}/messages", response_model=MessageListResponse)
async def get_patient_conversation_messages(
    conversation_id: str,
    limit: int = Query(50, ge=1, le=100),
    before: Optional[datetime] = None,
    current_patient: Patient = Depends(get_current_patient)
):
    """
    Get messages in a conversation for patient.
    
    Requires patient authentication.
    """
    # Verify access
    conversation = await MessageService.get_conversation_by_id(
        conversation_id=conversation_id,
        patient_id=current_patient.patient_id
    )
    
    messages, total, has_more = await MessageService.get_messages(
        conversation_id=conversation_id,
        limit=limit,
        before=before
    )
    
    return MessageListResponse(messages=messages, total=total, has_more=has_more)


@router.post("/patient/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_message_as_patient(
    conversation_id: str,
    request: MessageCreate,
    current_patient: Patient = Depends(get_current_patient)
):
    """
    Send a message in a conversation as patient.
    
    Requires patient authentication.
    """
    # Verify access
    conversation = await MessageService.get_conversation_by_id(
        conversation_id=conversation_id,
        patient_id=current_patient.patient_id
    )
    
    message = await MessageService.send_message(
        conversation_id=conversation_id,
        sender_type="patient",
        sender_id=current_patient.patient_id,
        sender_name=current_patient.name,
        content=request.content,
        attachment_url=request.attachment_url,
        attachment_type=request.attachment_type
    )
    
    return message


@router.post("/patient/conversations/{conversation_id}/read", response_model=MessageStatusResponse)
async def mark_messages_read_as_patient(
    conversation_id: str,
    current_patient: Patient = Depends(get_current_patient)
):
    """
    Mark all messages in a conversation as read.
    
    Requires patient authentication.
    """
    # Verify access
    conversation = await MessageService.get_conversation_by_id(
        conversation_id=conversation_id,
        patient_id=current_patient.patient_id
    )
    
    count = await MessageService.mark_messages_as_read(
        conversation_id=conversation_id,
        reader_type="patient"
    )
    
    return MessageStatusResponse(message=f"Marked {count} messages as read")


@router.get("/patient/unread-count")
async def get_patient_unread_count(
    current_patient: Patient = Depends(get_current_patient)
):
    """
    Get total unread message count for the patient.
    
    Requires patient authentication.
    """
    count = await MessageService.get_unread_count_for_patient(current_patient.patient_id)
    
    return {"unread_count": count}
