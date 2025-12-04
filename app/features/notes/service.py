# Notes Feature - Service

from typing import List, Tuple, Optional
from bson import ObjectId
from app.features.notes.models import Note
from app.features.notes.schemas import NoteCreate, NoteUpdate, NoteResponse, NoteListResponse
from app.features.patients.models import Patient
from app.core.logging import logger
from app.shared.exceptions import NotFoundException, ForbiddenException


class NoteService:
    """Service class for note operations."""
    
    @staticmethod
    def _note_to_response(note: Note) -> NoteResponse:
        """Convert Note document to response schema."""
        return NoteResponse(
            id=str(note.id),
            clinic_id=note.clinic_id,
            patient_id=note.patient_id,
            user_id=note.user_id,
            provider_name=note.provider_name,
            title=note.title,
            content=note.content,
            is_shared=note.is_shared,
            created_at=note.created_at,
            updated_at=note.updated_at,
        )
    
    @staticmethod
    async def create_note(
        clinic_id: str,
        user_id: str,
        provider_name: str,
        note_data: NoteCreate
    ) -> NoteResponse:
        """
        Create a new note for a patient.
        
        Args:
            clinic_id: Clinic ID
            user_id: Doctor's user ID
            provider_name: Doctor's display name
            note_data: Note creation data
            
        Returns:
            Created note response
        """
        # Verify patient exists in the clinic
        patient = await Patient.find_one(
            Patient.patient_id == note_data.patient_id,
            Patient.clinic_id == clinic_id
        )
        
        if not patient:
            raise NotFoundException("Patient not found in your clinic")
        
        # Create note
        note = Note(
            clinic_id=clinic_id,
            patient_id=note_data.patient_id,
            user_id=user_id,
            provider_name=provider_name,
            title=note_data.title,
            content=note_data.content,
            is_shared=note_data.is_shared,
        )
        await note.insert()
        
        logger.info(f"Created note '{note.title}' for patient {note_data.patient_id} by {provider_name} (is_shared={note.is_shared})")
        
        return NoteService._note_to_response(note)
    
    @staticmethod
    async def get_notes_for_patient(
        clinic_id: str,
        patient_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[NoteResponse], int]:
        """
        Get all notes for a patient (doctor view - sees all notes).
        
        Args:
            clinic_id: Clinic ID
            patient_id: Patient ID
            limit: Max number of notes
            offset: Pagination offset
            
        Returns:
            Tuple of (notes list, total count)
        """
        # Verify patient exists in the clinic
        patient = await Patient.find_one(
            Patient.patient_id == patient_id,
            Patient.clinic_id == clinic_id
        )
        
        if not patient:
            raise NotFoundException("Patient not found in your clinic")
        
        # Get all notes for this patient (not deleted)
        query = Note.find(
            Note.clinic_id == clinic_id,
            Note.patient_id == patient_id,
            Note.is_deleted == False
        ).sort([("created_at", -1)])
        
        total = await query.count()
        notes = await query.skip(offset).limit(limit).to_list()
        
        result = [NoteService._note_to_response(note) for note in notes]
        
        return result, total
    
    @staticmethod
    async def get_shared_notes_for_patient(
        patient_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[NoteResponse], int]:
        """
        Get shared notes for a patient (patient view - only sees shared notes).
        
        Args:
            patient_id: Patient ID
            limit: Max number of notes
            offset: Pagination offset
            
        Returns:
            Tuple of (notes list, total count)
        """
        logger.info(f"Fetching shared notes for patient {patient_id}")
        
        # Get only shared notes for this patient (not deleted)
        query = Note.find(
            Note.patient_id == patient_id,
            Note.is_shared == True,
            Note.is_deleted == False
        ).sort([("created_at", -1)])
        
        total = await query.count()
        notes = await query.skip(offset).limit(limit).to_list()
        
        logger.info(f"Found {total} shared notes for patient {patient_id} (returning {len(notes)})")
        
        result = [NoteService._note_to_response(note) for note in notes]
        
        return result, total
    
    @staticmethod
    async def get_note_by_id(note_id: str, clinic_id: str) -> Note:
        """
        Get a note by ID with clinic access check.
        
        Args:
            note_id: Note ID
            clinic_id: Clinic ID for access check
            
        Returns:
            Note document
            
        Raises:
            NotFoundException: If note not found or access denied
        """
        try:
            note = await Note.get(ObjectId(note_id))
        except Exception:
            raise NotFoundException("Note not found")
        
        if not note or note.is_deleted:
            raise NotFoundException("Note not found")
        
        if note.clinic_id != clinic_id:
            raise ForbiddenException("You don't have access to this note")
        
        return note
    
    @staticmethod
    async def update_note(
        note_id: str,
        clinic_id: str,
        user_id: str,
        update_data: NoteUpdate
    ) -> NoteResponse:
        """
        Update a note.
        
        Args:
            note_id: Note ID
            clinic_id: Clinic ID for access check
            user_id: User ID (for logging)
            update_data: Update data
            
        Returns:
            Updated note response
        """
        note = await NoteService.get_note_by_id(note_id, clinic_id)
        
        # Update fields if provided
        if update_data.title is not None:
            note.title = update_data.title
        if update_data.content is not None:
            note.content = update_data.content
        if update_data.is_shared is not None:
            note.is_shared = update_data.is_shared
            logger.info(f"Updating note {note_id} is_shared to {update_data.is_shared}")
        
        await note.save()
        
        logger.info(f"Updated note {note_id} by user {user_id} (is_shared={note.is_shared})")
        
        return NoteService._note_to_response(note)
    
    @staticmethod
    async def delete_note(note_id: str, clinic_id: str, user_id: str) -> bool:
        """
        Soft delete a note.
        
        Args:
            note_id: Note ID
            clinic_id: Clinic ID for access check
            user_id: User ID (for logging)
            
        Returns:
            True if deleted successfully
        """
        note = await NoteService.get_note_by_id(note_id, clinic_id)
        
        # Soft delete
        note.is_deleted = True
        await note.save()
        
        logger.info(f"Deleted note {note_id} by user {user_id}")
        
        return True
