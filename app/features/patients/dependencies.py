# Patient Management Feature - Dependencies

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.features.patients.models import Patient
from app.features.patients.service import PatientService
from app.core.security import decode_token
from app.shared.exceptions import CredentialsException


# HTTP Bearer security scheme for patients
patient_security = HTTPBearer()


async def get_current_patient(
    credentials: HTTPAuthorizationCredentials = Depends(patient_security)
) -> Patient:
    """
    Dependency to get current authenticated patient.
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        Patient: Current authenticated patient
        
    Raises:
        CredentialsException: If credentials are invalid
    """
    token = credentials.credentials
    
    # Decode token
    payload = decode_token(token)
    if payload is None:
        raise CredentialsException("Invalid authentication credentials")
    
    # Check if this is a patient token
    token_type = payload.get("type")
    if token_type != "patient":
        raise CredentialsException("Invalid token type. This endpoint requires patient authentication.")
    
    # Get patient ID from token (MongoDB _id stored in "sub")
    patient_mongo_id: str = payload.get("sub")
    if patient_mongo_id is None:
        raise CredentialsException("Invalid authentication credentials")
    
    # Get patient from database
    try:
        patient = await PatientService.get_patient_by_mongo_id(patient_mongo_id)
    except Exception:
        raise CredentialsException("Patient not found")
    
    if not patient.is_active:
        raise CredentialsException("Your account has been deactivated. Please contact your clinic.")
    
    return patient


async def get_current_active_patient(
    current_patient: Patient = Depends(get_current_patient)
) -> Patient:
    """
    Dependency to get current active patient.
    
    Args:
        current_patient: Current patient from get_current_patient
        
    Returns:
        Patient: Current active patient
        
    Raises:
        HTTPException: If patient is inactive
    """
    if not current_patient.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive patient account"
        )
    return current_patient
