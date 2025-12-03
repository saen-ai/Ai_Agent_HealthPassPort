# Clinic router
from fastapi import APIRouter, Depends, status
from app.features.clinic.models import Clinic
from app.features.clinic.schemas import ClinicResponse, UpdateClinicRequest
from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User
from app.shared.exceptions import NotFoundException
from app.core.logging import logger

router = APIRouter(prefix="/clinic", tags=["Clinic"])


@router.get("/me", response_model=ClinicResponse)
async def get_my_clinic(current_user: User = Depends(get_current_user)):
    """
    Get the current user's clinic.
    
    Requires authentication.
    """
    # Find clinic by owner_id or clinic_id from user
    clinic = None
    
    if current_user.clinic_id:
        clinic = await Clinic.get(current_user.clinic_id)
    
    if not clinic:
        # Try to find by owner_id
        clinic = await Clinic.find_one(Clinic.owner_id == str(current_user.id))
    
    if not clinic:
        raise NotFoundException("Clinic not found. Please contact support.")
    
    return ClinicResponse(
        id=str(clinic.id),
        name=clinic.name,
        owner_id=clinic.owner_id,
        address=clinic.address or "",
        logo_url=clinic.logo_url or "",
        primary_color=clinic.primary_color,
        created_at=clinic.created_at,
        updated_at=clinic.updated_at,
    )


@router.patch("/me", response_model=ClinicResponse)
async def update_my_clinic(
    update_data: UpdateClinicRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update the current user's clinic settings.
    
    Requires authentication.
    
    - **name**: Clinic name (optional)
    - **address**: Clinic address (optional)
    - **logo_url**: URL to clinic logo (optional)
    - **primary_color**: Primary brand color as hex (optional, e.g. #0ea5e9)
    """
    # Find clinic
    clinic = None
    
    if current_user.clinic_id:
        clinic = await Clinic.get(current_user.clinic_id)
    
    if not clinic:
        clinic = await Clinic.find_one(Clinic.owner_id == str(current_user.id))
    
    if not clinic:
        raise NotFoundException("Clinic not found. Please contact support.")
    
    # Update fields that are provided
    update_dict = update_data.model_dump(exclude_unset=True)
    
    for field, value in update_dict.items():
        setattr(clinic, field, value)
    
    await clinic.save()
    
    logger.info(f"Clinic {clinic.id} updated by user {current_user.email}")
    
    return ClinicResponse(
        id=str(clinic.id),
        name=clinic.name,
        owner_id=clinic.owner_id,
        address=clinic.address or "",
        logo_url=clinic.logo_url or "",
        primary_color=clinic.primary_color,
        created_at=clinic.created_at,
        updated_at=clinic.updated_at,
    )
