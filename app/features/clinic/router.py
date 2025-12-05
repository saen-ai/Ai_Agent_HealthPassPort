# Clinic router
from fastapi import APIRouter, Depends, status
from bson import ObjectId
from app.features.clinic.models import Clinic
from app.features.clinic.schemas import ClinicResponse, UpdateClinicRequest, ClinicBrandingResponse
from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User
from app.shared.exceptions import NotFoundException
from app.core.logging import logger

router = APIRouter(prefix="/clinic", tags=["Clinic"])


@router.get("/me", response_model=ClinicResponse)
async def get_my_clinic(current_user: User = Depends(get_current_user)):
    """
    Get the current user's clinic.
    Creates a clinic if one doesn't exist.
    
    Requires authentication.
    """
    # Find clinic by owner_id or clinic_id from user
    clinic = None
    
    try:
        if current_user.clinic_id:
            clinic = await Clinic.get(current_user.clinic_id)
    except Exception:
        clinic = None
    
    if not clinic:
        # Try to find by owner_id
        clinic = await Clinic.find_one(Clinic.owner_id == str(current_user.id))
    
    # If no clinic exists, create one
    if not clinic:
        clinic = Clinic(
            name=current_user.name + "'s Clinic",
            owner_id=str(current_user.id),
            address="",
            logo_url="",
            primary_color="#0ea5e9"
        )
        await clinic.save()
        
        # Update user's clinic_id
        current_user.clinic_id = str(clinic.id)
        await current_user.save()
        
        logger.info(f"Created new clinic {clinic.id} for user {current_user.email}")
    
    # Handle backward compatibility: use color_theme if primary_color doesn't exist
    primary_color = getattr(clinic, 'primary_color', None) or getattr(clinic, 'color_theme', None) or "#0ea5e9"
    
    # If primary_color doesn't exist but color_theme does, migrate it
    if not hasattr(clinic, 'primary_color') or not clinic.primary_color:
        if hasattr(clinic, 'color_theme') and clinic.color_theme:
            clinic.primary_color = clinic.color_theme
            await clinic.save()
        else:
            clinic.primary_color = "#0ea5e9"
            await clinic.save()
    
    return ClinicResponse(
        id=str(clinic.id),
        name=clinic.name,
        owner_id=clinic.owner_id or str(current_user.id),
        address=clinic.address or "",
        logo_url=clinic.logo_url or "",
        primary_color=clinic.primary_color or primary_color,
        phone=clinic.phone or "",
        email=clinic.email or "",
        latitude=clinic.latitude,
        longitude=clinic.longitude,
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
    - **phone**: Clinic phone number (optional)
    - **email**: Clinic email address (optional)
    - **latitude**: Clinic latitude for Google Maps (optional)
    - **longitude**: Clinic longitude for Google Maps (optional)
    """
    # Find clinic
    clinic = None
    
    try:
        if current_user.clinic_id:
            clinic = await Clinic.get(current_user.clinic_id)
    except Exception:
        clinic = None
    
    if not clinic:
        clinic = await Clinic.find_one(Clinic.owner_id == str(current_user.id))
    
    # If no clinic exists, create one
    if not clinic:
        clinic = Clinic(
            name=current_user.name + "'s Clinic",
            owner_id=str(current_user.id),
            address="",
            logo_url="",
            primary_color="#0ea5e9"
        )
        await clinic.save()
        
        # Update user's clinic_id
        current_user.clinic_id = str(clinic.id)
        await current_user.save()
    
    # Update fields that are provided
    update_dict = update_data.model_dump(exclude_unset=True)
    
    for field, value in update_dict.items():
        setattr(clinic, field, value)
    
    await clinic.save()
    
    logger.info(f"Clinic {clinic.id} updated by user {current_user.email}")
    
    # Handle backward compatibility for primary_color
    primary_color = getattr(clinic, 'primary_color', None) or getattr(clinic, 'color_theme', None) or "#0ea5e9"
    
    return ClinicResponse(
        id=str(clinic.id),
        name=clinic.name,
        owner_id=clinic.owner_id or str(current_user.id),
        address=clinic.address or "",
        logo_url=clinic.logo_url or "",
        primary_color=clinic.primary_color if hasattr(clinic, 'primary_color') and clinic.primary_color else primary_color,
        phone=clinic.phone or "",
        email=clinic.email or "",
        latitude=clinic.latitude,
        longitude=clinic.longitude,
        created_at=clinic.created_at,
        updated_at=clinic.updated_at,
    )


@router.get("/{clinic_id}/branding", response_model=ClinicBrandingResponse)
async def get_clinic_branding(clinic_id: str):
    """
    Get clinic branding information (public endpoint, no authentication required).
    
    This endpoint allows patients to fetch the latest clinic branding (logo and color)
    even when their authentication token has expired.
    
    - **clinic_id**: MongoDB ObjectId of the clinic
    """
    try:
        clinic = await Clinic.get(ObjectId(clinic_id))
    except Exception:
        raise NotFoundException("Clinic not found")
    
    # Handle backward compatibility: use color_theme if primary_color doesn't exist
    primary_color = getattr(clinic, 'primary_color', None) or getattr(clinic, 'color_theme', None) or "#0ea5e9"
    
    # Ensure color is properly formatted (with #)
    if primary_color and not primary_color.startswith('#'):
        primary_color = '#' + primary_color
    
    return ClinicBrandingResponse(
        id=str(clinic.id),
        name=clinic.name,
        logo_url=clinic.logo_url or "",
        primary_color=primary_color,
    )
