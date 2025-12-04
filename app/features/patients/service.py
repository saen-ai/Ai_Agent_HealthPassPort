# Patient Management Feature - Service

from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from app.features.patients.models import Patient
from app.features.patients.schemas import (
    CreatePatientRequest,
    UpdatePatientRequest,
    PatientResponse,
    PatientLoginRequest,
    ClinicInfo,
)
from app.features.clinic.models import Clinic
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.logging import logger
from app.core.email import send_patient_welcome_email
from app.shared.exceptions import NotFoundException, CredentialsException, ConflictException


class PatientService:
    """Service class for patient management operations."""
    
    @staticmethod
    async def generate_patient_id(clinic_id: str) -> str:
        """Generate a unique patient ID for a clinic (e.g., P00001)."""
        # Count existing patients for this clinic to generate next ID
        patient_count = await Patient.find(Patient.clinic_id == clinic_id).count()
        next_number = patient_count + 1
        return f"P{next_number:05d}"
    
    @staticmethod
    async def create_patient(clinic_id: str, request: CreatePatientRequest, plain_password: Optional[str] = None) -> Patient:
        """Create a new patient for a clinic."""
        # Check if email already exists for this clinic
        existing_patient = await Patient.find_one(
            Patient.clinic_id == clinic_id,
            Patient.email == request.email
        )
        if existing_patient:
            raise ConflictException("A patient with this email already exists in your clinic")
        
        # Generate unique patient ID
        patient_id = await PatientService.generate_patient_id(clinic_id)
        
        # Store plain password for email before hashing
        password_for_email = plain_password or request.password
        
        # Hash the password
        password_hash = get_password_hash(request.password)
        
        # Convert medications to dict format
        medications = [med.model_dump() for med in request.medications] if request.medications else []
        
        # Create patient
        patient = Patient(
            patient_id=patient_id,
            clinic_id=clinic_id,
            email=request.email,
            password_hash=password_hash,
            name=request.name,
            date_of_birth=request.date_of_birth,
            gender=request.gender,
            phone=request.phone,
            address=request.address,
            conditions=request.conditions or [],
            medications=medications,
            allergies=request.allergies or [],
            is_active=True,
        )
        
        await patient.save()
        logger.info(f"Created patient {patient_id} for clinic {clinic_id}")
        
        # Get clinic name for email
        try:
            clinic = await Clinic.find_one({"_id": ObjectId(clinic_id)})
            clinic_name = clinic.name if clinic else "Health Passport"
        except Exception:
            clinic_name = "Health Passport"
        
        # Send welcome email with credentials
        try:
            await send_patient_welcome_email(
                email=request.email,
                name=request.name,
                patient_id=patient_id,
                password=password_for_email,
                clinic_name=clinic_name
            )
            logger.info(f"Sent welcome email to patient {patient_id}")
        except Exception as e:
            # Don't fail patient creation if email fails
            logger.error(f"Failed to send welcome email to patient {patient_id}: {e}")
        
        return patient
    
    @staticmethod
    async def get_patients_by_clinic(clinic_id: str, include_inactive: bool = False) -> List[Patient]:
        """Get all patients for a clinic."""
        query = Patient.find(Patient.clinic_id == clinic_id)
        
        if not include_inactive:
            query = query.find(Patient.is_active == True)
        
        patients = await query.sort(-Patient.created_at).to_list()
        return patients
    
    @staticmethod
    async def get_patient_by_id(patient_id: str, clinic_id: Optional[str] = None) -> Patient:
        """Get a patient by their patient_id."""
        query_conditions = [Patient.patient_id == patient_id]
        
        if clinic_id:
            query_conditions.append(Patient.clinic_id == clinic_id)
        
        patient = await Patient.find_one(*query_conditions)
        
        if not patient:
            raise NotFoundException("Patient not found")
        
        return patient
    
    @staticmethod
    async def get_patient_by_mongo_id(mongo_id: str) -> Patient:
        """Get a patient by their MongoDB _id."""
        patient = await Patient.get(mongo_id)
        
        if not patient:
            raise NotFoundException("Patient not found")
        
        return patient
    
    @staticmethod
    async def update_patient(
        patient_id: str,
        clinic_id: str,
        request: UpdatePatientRequest
    ) -> Patient:
        """Update patient information."""
        patient = await PatientService.get_patient_by_id(patient_id, clinic_id)
        
        # Update fields that are provided
        update_dict = request.model_dump(exclude_unset=True)
        
        # Convert medications if provided
        if 'medications' in update_dict and update_dict['medications']:
            update_dict['medications'] = [
                med.model_dump() if hasattr(med, 'model_dump') else med 
                for med in update_dict['medications']
            ]
        
        for field, value in update_dict.items():
            setattr(patient, field, value)
        
        patient.updated_at = datetime.utcnow()
        await patient.save()
        
        logger.info(f"Updated patient {patient_id}")
        return patient
    
    @staticmethod
    async def delete_patient(patient_id: str, clinic_id: str) -> None:
        """Permanently delete a patient from the database."""
        patient = await PatientService.get_patient_by_id(patient_id, clinic_id)
        
        await patient.delete()
        
        logger.info(f"Permanently deleted patient {patient_id}")
    
    @staticmethod
    async def patient_login(request: PatientLoginRequest) -> tuple[Patient, str, Clinic]:
        """Authenticate a patient and return token with clinic info."""
        # Find patient by patient_id
        patient = await Patient.find_one(Patient.patient_id == request.patient_id)
        
        if not patient:
            raise CredentialsException("Invalid Patient ID or password")
        
        if not patient.is_active:
            raise CredentialsException("Your account has been deactivated. Please contact your clinic.")
        
        # Verify password
        if not verify_password(request.password, patient.password_hash):
            raise CredentialsException("Invalid Patient ID or password")
        
        # Get clinic info - use raw MongoDB query for _id lookup
        try:
            clinic = await Clinic.find_one({"_id": ObjectId(patient.clinic_id)})
        except Exception:
            clinic = None
        
        if not clinic:
            raise NotFoundException("Clinic not found")
        
        # Create access token with patient type
        access_token = create_access_token(
            data={
                "sub": str(patient.id),
                "type": "patient",
                "patient_id": patient.patient_id,
                "clinic_id": patient.clinic_id,
            }
        )
        
        logger.info(f"Patient {patient.patient_id} logged in successfully")
        
        return patient, access_token, clinic
    
    @staticmethod
    def patient_to_response(patient: Patient) -> PatientResponse:
        """Convert Patient model to response schema."""
        return PatientResponse(
            id=str(patient.id),
            patient_id=patient.patient_id,
            clinic_id=patient.clinic_id,
            email=patient.email,
            name=patient.name,
            date_of_birth=patient.date_of_birth,
            gender=patient.gender,
            phone=patient.phone,
            address=patient.address,
            avatar_url=patient.avatar_url,
            conditions=patient.conditions or [],
            medications=patient.medications or [],
            allergies=patient.allergies or [],
            is_active=patient.is_active,
            created_at=patient.created_at,
            updated_at=patient.updated_at,
        )
    
    @staticmethod
    def clinic_to_info(clinic: Clinic) -> ClinicInfo:
        """Convert Clinic model to ClinicInfo schema."""
        return ClinicInfo(
            id=str(clinic.id),
            name=clinic.name,
            logo_url=clinic.logo_url,
            primary_color=clinic.primary_color or "#0ea5e9",
            address=clinic.address,
        )
