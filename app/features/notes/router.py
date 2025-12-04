# Notes Feature - Router

from fastapi import APIRouter, Depends, Query
from app.features.auth.models import User
from app.features.auth.dependencies import get_current_user
from app.features.patients.models import Patient
from app.features.patients.dependencies import get_current_patient
from app.features.notes.schemas import (
    NoteCreate,
    NoteUpdate,
    NoteResponse,
    NoteListResponse,
)
from app.features.notes.service import NoteService


router = APIRouter(prefix="/notes", tags=["Notes"])


# ==================== Doctor Endpoints ====================

@router.post("", response_model=NoteResponse)
async def create_note(
    note_data: NoteCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new note for a patient.
    
    - **patient_id**: Patient ID (e.g., P00001)
    - **title**: Note title
    - **content**: Note content
    - **is_shared**: Whether the note is shared with the patient (default: True)
    """
    return await NoteService.create_note(
        clinic_id=current_user.clinic_id,
        user_id=str(current_user.id),
        provider_name=current_user.name,
        note_data=note_data
    )


# ==================== Patient Endpoints ====================
# NOTE: This endpoint MUST be defined BEFORE /patient/{patient_id} to avoid route conflict
# FastAPI matches routes in order of definition, so static routes must come before dynamic ones

@router.get("/patient/my-notes", response_model=NoteListResponse)
async def get_my_notes(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_patient: Patient = Depends(get_current_patient)
):
    """
    Get shared notes for the current patient.
    Only returns notes that have been marked as shared by the doctor.
    """
    notes, total = await NoteService.get_shared_notes_for_patient(
        patient_id=current_patient.patient_id,
        limit=limit,
        offset=offset
    )
    
    return NoteListResponse(
        notes=notes,
        total=total,
        has_more=offset + len(notes) < total
    )


# ==================== More Doctor Endpoints ====================

@router.get("/patient/{patient_id}", response_model=NoteListResponse)
async def get_patient_notes(
    patient_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user)
):
    """
    Get all notes for a patient (doctor view - sees all notes including private).
    
    - **patient_id**: Patient ID (e.g., P00001)
    """
    notes, total = await NoteService.get_notes_for_patient(
        clinic_id=current_user.clinic_id,
        patient_id=patient_id,
        limit=limit,
        offset=offset
    )
    
    return NoteListResponse(
        notes=notes,
        total=total,
        has_more=offset + len(notes) < total
    )


@router.patch("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str,
    update_data: NoteUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing note.
    
    - **note_id**: Note ID
    - **title**: New title (optional)
    - **content**: New content (optional)
    - **is_shared**: New visibility setting (optional)
    """
    return await NoteService.update_note(
        note_id=note_id,
        clinic_id=current_user.clinic_id,
        user_id=str(current_user.id),
        update_data=update_data
    )


@router.delete("/{note_id}")
async def delete_note(
    note_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a note (soft delete).
    
    - **note_id**: Note ID to delete
    """
    await NoteService.delete_note(
        note_id=note_id,
        clinic_id=current_user.clinic_id,
        user_id=str(current_user.id)
    )
    return {"message": "Note deleted successfully"}
