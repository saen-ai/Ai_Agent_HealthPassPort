from fastapi import APIRouter, Depends, UploadFile, File, status
from app.features.files.service import FileService
from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User
from app.features.clinic.models import Clinic
from app.shared.exceptions import BadRequestException, NotFoundException
from app.core.logging import logger

router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/upload-profile-picture", status_code=status.HTTP_200_OK)
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload profile picture to GCP Storage.
    Automatically deletes the previous profile picture if one exists.
    
    Requires authentication.
    
    - **file**: Image file (JPG or PNG, max 5MB)
    
    Returns:
        dict: Public URL of uploaded image
    """
    if not file.filename:
        raise BadRequestException("No file provided")
    
    try:
        # Get the old profile picture URL to delete after successful upload
        old_profile_picture_url = current_user.profile_picture_url
        
        public_url = await FileService.upload_profile_picture(
            file=file,
            user_id=str(current_user.id),
            old_profile_picture_url=old_profile_picture_url
        )
        
        # Update user's profile_picture_url
        current_user.profile_picture_url = public_url
        await current_user.save()
        
        logger.info(f"Profile picture updated for user {current_user.email}")
        
        return {
            "url": public_url,
            "message": "Profile picture uploaded successfully"
        }
    except Exception as e:
        logger.error(f"Error in upload_profile_picture: {str(e)}")
        raise


@router.post("/upload-clinic-logo", status_code=status.HTTP_200_OK)
async def upload_clinic_logo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload clinic logo to GCP Storage.
    Automatically deletes the previous logo if one exists.
    
    Requires authentication.
    
    - **file**: Image file (JPG or PNG, max 2MB)
    
    Returns:
        dict: URL of uploaded logo
    """
    if not file.filename:
        raise BadRequestException("No file provided")
    
    # Find the user's clinic
    clinic = None
    if current_user.clinic_id:
        clinic = await Clinic.get(current_user.clinic_id)
    
    if not clinic:
        clinic = await Clinic.find_one(Clinic.owner_id == str(current_user.id))
    
    if not clinic:
        raise NotFoundException("Clinic not found")
    
    try:
        old_logo_url = clinic.logo_url
        
        logo_url = await FileService.upload_clinic_logo(
            file=file,
            clinic_id=str(clinic.id),
            old_logo_url=old_logo_url
        )
        
        # Update clinic's logo_url
        clinic.logo_url = logo_url
        await clinic.save()
        
        logger.info(f"Clinic logo updated for clinic {clinic.id}")
        
        return {
            "url": logo_url,
            "message": "Clinic logo uploaded successfully"
        }
    except Exception as e:
        logger.error(f"Error in upload_clinic_logo: {str(e)}")
        raise
