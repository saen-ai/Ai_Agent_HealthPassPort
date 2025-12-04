# Patient Management Feature - Router

from fastapi import APIRouter, Depends, status
from typing import List
from bson import ObjectId
from app.features.patients.models import Patient
from app.features.patients.schemas import (
    CreatePatientRequest,
    UpdatePatientRequest,
    PatientResponse,
    PatientListResponse,
    PatientLoginRequest,
    PatientLoginResponse,
    PatientMeResponse,
    CreatePatientResponse,
    PatientForgotPasswordRequest,
    PatientResetPasswordRequest,
    NotificationSettingsRequest,
    MessageResponse,
)
from app.features.patients.service import PatientService
from app.features.patients.dependencies import get_current_patient
from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User
from app.features.clinic.models import Clinic
from app.core.logging import logger


router = APIRouter(prefix="/patients", tags=["Patients"])


# ============== Doctor/Admin Endpoints (Require User Auth) ==============

@router.post("", response_model=CreatePatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    request: CreatePatientRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new patient for the current user's clinic.
    
    Requires doctor/admin authentication.
    
    Returns the created patient with their generated Patient ID.
    """
    if not current_user.clinic_id:
        from app.shared.exceptions import BadRequestException
        raise BadRequestException("You must be associated with a clinic to add patients")
    
    patient = await PatientService.create_patient(current_user.clinic_id, request)
    
    return CreatePatientResponse(
        patient=PatientService.patient_to_response(patient),
        generated_patient_id=patient.patient_id,
        message=f"Patient created successfully. Patient ID: {patient.patient_id}"
    )


@router.get("", response_model=PatientListResponse)
async def list_patients(
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user)
):
    """
    List all patients for the current user's clinic.
    
    Requires doctor/admin authentication.
    
    - **include_inactive**: Include deactivated patients (default: false)
    """
    if not current_user.clinic_id:
        from app.shared.exceptions import BadRequestException
        raise BadRequestException("You must be associated with a clinic to view patients")
    
    patients = await PatientService.get_patients_by_clinic(
        current_user.clinic_id, 
        include_inactive=include_inactive
    )
    
    return PatientListResponse(
        patients=[PatientService.patient_to_response(p) for p in patients],
        total=len(patients)
    )


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific patient by their Patient ID.
    
    Requires doctor/admin authentication.
    """
    if not current_user.clinic_id:
        from app.shared.exceptions import BadRequestException
        raise BadRequestException("You must be associated with a clinic to view patients")
    
    patient = await PatientService.get_patient_by_id(patient_id, current_user.clinic_id)
    
    return PatientService.patient_to_response(patient)


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: str,
    request: UpdatePatientRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update a patient's information.
    
    Requires doctor/admin authentication.
    """
    if not current_user.clinic_id:
        from app.shared.exceptions import BadRequestException
        raise BadRequestException("You must be associated with a clinic to update patients")
    
    patient = await PatientService.update_patient(patient_id, current_user.clinic_id, request)
    
    return PatientService.patient_to_response(patient)


@router.delete("/{patient_id}", response_model=MessageResponse)
async def delete_patient(
    patient_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Permanently delete a patient from the database.
    
    Requires doctor/admin authentication.
    
    WARNING: This action cannot be undone. The patient record will be completely removed.
    """
    if not current_user.clinic_id:
        from app.shared.exceptions import BadRequestException
        raise BadRequestException("You must be associated with a clinic to delete patients")
    
    await PatientService.delete_patient(patient_id, current_user.clinic_id)
    
    return MessageResponse(message=f"Patient {patient_id} has been permanently deleted")


# ============== Patient Authentication Endpoints (No Auth Required) ==============

@router.post("/auth/login", response_model=PatientLoginResponse)
async def patient_login(request: PatientLoginRequest):
    """
    Authenticate a patient using their Patient ID and password.
    
    No authentication required.
    
    Returns access token along with patient and clinic information.
    """
    patient, access_token, clinic = await PatientService.patient_login(request)
    
    return PatientLoginResponse(
        access_token=access_token,
        token_type="bearer",
        patient=PatientService.patient_to_response(patient),
        clinic=PatientService.clinic_to_info(clinic),
    )


@router.post("/auth/forgot-password", response_model=MessageResponse)
async def patient_forgot_password(request: PatientForgotPasswordRequest):
    """
    Send password reset email to patient.
    
    No authentication required.
    
    - **patient_id**: Patient ID (e.g., P00001)
    - **email**: Patient's email address
    
    Note: For security, this endpoint always returns success even if patient is not found.
    """
    await PatientService.forgot_password(request.patient_id, request.email)
    
    return MessageResponse(
        message="If your Patient ID and email match our records, a password reset link has been sent to your email"
    )


@router.post("/auth/reset-password", response_model=MessageResponse)
async def patient_reset_password(request: PatientResetPasswordRequest):
    """
    Reset patient password using token from email.
    
    No authentication required.
    
    - **token**: Password reset token from email
    - **new_password**: New password (min 8 characters)
    """
    await PatientService.reset_password(request.token, request.new_password)
    
    return MessageResponse(message="Password reset successfully")


# ============== Patient Authenticated Endpoints ==============

@router.get("/auth/me", response_model=PatientMeResponse)
async def get_current_patient_info(
    current_patient: Patient = Depends(get_current_patient)
):
    """
    Get current authenticated patient's information.
    
    Requires patient authentication.
    """
    # Get clinic info - use raw MongoDB query for _id lookup
    try:
        clinic = await Clinic.find_one({"_id": ObjectId(current_patient.clinic_id)})
    except Exception:
        clinic = None
    
    return PatientMeResponse(
        patient=PatientService.patient_to_response(current_patient),
        clinic=PatientService.clinic_to_info(clinic) if clinic else None,
    )


@router.patch("/auth/notification-settings", response_model=PatientResponse)
async def update_patient_notification_settings(
    settings: NotificationSettingsRequest,
    current_patient: Patient = Depends(get_current_patient)
):
    """
    Update current patient's notification preferences.
    
    Requires patient authentication.
    
    - **notifications_enabled**: Enable or disable browser notifications
    """
    current_patient.notifications_enabled = settings.notifications_enabled
    await current_patient.save()
    
    return PatientService.patient_to_response(current_patient)
