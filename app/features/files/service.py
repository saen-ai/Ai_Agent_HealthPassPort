from typing import Optional
import uuid
from datetime import datetime, timedelta
from fastapi import UploadFile
from google.cloud import storage
from PIL import Image
import io
from app.config import settings
from app.core.logging import logger
from app.shared.exceptions import BadRequestException


class FileService:
    """Service for handling file uploads to GCP Cloud Storage."""
    
    _client: Optional[storage.Client] = None
    
    @classmethod
    def get_client(cls) -> storage.Client:
        """Get or create GCP Storage client."""
        if cls._client is None:
            # Validate configuration
            if not settings.GCP_PROJECT_ID:
                raise BadRequestException(
                    "GCP_PROJECT_ID is not configured. Please set it in your .env file."
                )
            
            if not settings.GCP_STORAGE_BUCKET_NAME:
                raise BadRequestException(
                    "GCP_STORAGE_BUCKET_NAME is not configured. Please set it in your .env file."
                )
            
            if settings.GOOGLE_APPLICATION_CREDENTIALS:
                import os
                if not os.path.exists(settings.GOOGLE_APPLICATION_CREDENTIALS):
                    raise BadRequestException(
                        f"Service account key file not found: {settings.GOOGLE_APPLICATION_CREDENTIALS}"
                    )
                try:
                    cls._client = storage.Client.from_service_account_json(
                        settings.GOOGLE_APPLICATION_CREDENTIALS,
                        project=settings.GCP_PROJECT_ID
                    )
                    logger.info(f"GCP Storage client initialized with service account: {settings.GOOGLE_APPLICATION_CREDENTIALS}")
                except Exception as e:
                    logger.error(f"Failed to initialize GCP Storage client: {str(e)}")
                    raise BadRequestException(
                        f"Failed to initialize GCP Storage client. Please check your service account key file: {str(e)}"
                    )
            else:
                # Try to use default credentials
                try:
                    cls._client = storage.Client(project=settings.GCP_PROJECT_ID)
                    logger.info("GCP Storage client initialized with default credentials")
                except Exception as e:
                    logger.error(f"Failed to initialize GCP Storage client with default credentials: {str(e)}")
                    raise BadRequestException(
                        "GCP credentials not configured. Please set GOOGLE_APPLICATION_CREDENTIALS in your .env file."
                    )
        return cls._client
    
    @classmethod
    async def upload_profile_picture(
        cls,
        file: UploadFile,
        user_id: str
    ) -> str:
        """
        Upload profile picture to GCP Storage.
        
        Args:
            file: Uploaded file
            user_id: User ID for organizing files
        
        Returns:
            str: Public URL of uploaded file
        """
        # Validate file type
        allowed_types = ["image/jpeg", "image/jpg", "image/png"]
        if file.content_type not in allowed_types:
            raise BadRequestException(
                "Invalid file type. Only JPG and PNG images are allowed."
            )
        
        # Validate file size (5MB max)
        file_content = await file.read()
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > 5:
            raise BadRequestException(
                "File size exceeds 5MB limit. Please upload a smaller image."
            )
        
        # Validate and optimize image
        try:
            image = Image.open(io.BytesIO(file_content))
            # Convert to RGB if necessary (handles RGBA, P, etc.)
            if image.mode in ("RGBA", "P"):
                rgb_image = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "RGBA":
                    rgb_image.paste(image, mask=image.split()[3])  # Use alpha channel as mask
                else:
                    rgb_image.paste(image)
                image = rgb_image
            
            # Resize if too large (max 1024x1024)
            max_size = 1024
            if image.width > max_size or image.height > max_size:
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Convert to bytes
            output = io.BytesIO()
            image_format = "JPEG"  # Always save as JPEG for consistency
            image.save(output, format=image_format, quality=85, optimize=True)
            file_content = output.getvalue()
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            raise BadRequestException("Invalid image file. Please upload a valid image.")
        
        # Generate unique filename
        file_extension = "jpg"
        unique_filename = f"profile-pictures/{user_id}/{uuid.uuid4()}.{file_extension}"
        
        # Upload to GCP
        try:
            client = cls.get_client()
            bucket = client.bucket(settings.GCP_STORAGE_BUCKET_NAME)
            
            # Try to check if bucket exists (may fail due to permissions)
            try:
                if not bucket.exists():
                    raise BadRequestException(
                        f"Bucket '{settings.GCP_STORAGE_BUCKET_NAME}' does not exist. Please check your GCP configuration."
                    )
            except Exception as check_error:
                # If we can't check existence due to permissions, log warning but continue
                # The actual upload will fail if bucket doesn't exist or we don't have permissions
                logger.warning(f"Could not verify bucket existence (may be permission issue): {str(check_error)}")
            
            blob = bucket.blob(unique_filename)
            
            # Set content type and upload
            blob.content_type = "image/jpeg"
            blob.upload_from_string(file_content, content_type="image/jpeg")
            
            # Try to make public (may fail if bucket doesn't allow public access)
            try:
                blob.make_public()
                public_url = blob.public_url
            except Exception as public_error:
                logger.warning(f"Could not make blob public: {str(public_error)}. Using signed URL instead.")
                # Generate signed URL (valid for 1 year)
                public_url = blob.generate_signed_url(
                    expiration=timedelta(days=365),
                    method="GET"
                )
            
            logger.info(f"Successfully uploaded profile picture: {public_url}")
            return public_url
            
        except BadRequestException:
            # Re-raise BadRequestException as-is
            raise
        except Exception as e:
            logger.error(f"Error uploading to GCP: {str(e)}")
            error_message = str(e)
            if "403" in error_message or "permission" in error_message.lower():
                raise BadRequestException(
                    "Permission denied. Please check that the service account has Storage Admin or Storage Object Admin role on the bucket."
                )
            elif "404" in error_message or "not found" in error_message.lower():
                raise BadRequestException(
                    f"Bucket '{settings.GCP_STORAGE_BUCKET_NAME}' not found. Please verify the bucket name in your .env file."
                )
            else:
                raise BadRequestException(
                    f"Failed to upload image to GCP: {error_message}. Please check your GCP configuration."
                )
