# Patient Management Feature - Dependencies

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.features.patients.models import Patient
from app.features.patients.service import PatientService
from app.core.security import decode_token
from app.core.logging import logger
from app.shared.exceptions import CredentialsException, NotFoundException


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
        logger.warning("Failed to decode patient token")
        raise CredentialsException("Invalid authentication credentials")
    
    logger.debug(f"Decoded patient token payload: {list(payload.keys())}")
    
    # Check if this is a patient token
    token_type = payload.get("type")
    if token_type != "patient":
        logger.warning(f"Invalid token type: {token_type}, expected 'patient'")
        raise CredentialsException("Invalid token type. This endpoint requires patient authentication.")
    
    # Get patient ID from token (MongoDB _id stored in "sub")
    patient_mongo_id: str = payload.get("sub")
    if patient_mongo_id is None:
        logger.warning("Patient token missing 'sub' field")
        raise CredentialsException("Invalid authentication credentials")
    
    logger.debug(f"Looking up patient with mongo_id: {patient_mongo_id}")
    
    # Get patient from database
    try:
        patient = await PatientService.get_patient_by_mongo_id(patient_mongo_id)
        logger.debug(f"Found patient: {patient.patient_id} (active: {patient.is_active})")
    except NotFoundException:
        logger.warning(f"Patient not found with mongo_id: {patient_mongo_id}")
        raise CredentialsException("Patient not found. Please log in again.")
    except Exception as e:
        logger.error(f"Error getting patient by mongo_id {patient_mongo_id}: {type(e).__name__}: {e}")
        raise CredentialsException("Invalid authentication credentials")
    
    if not patient.is_active:
        logger.warning(f"Inactive patient attempted access: {patient.patient_id}")
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
