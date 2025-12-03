from typing import Optional
import uuid
from datetime import timedelta
from urllib.parse import urlparse
from fastapi import UploadFile
from google.cloud import storage
from google.cloud.exceptions import NotFound
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
    def extract_blob_path_from_url(cls, url: str) -> Optional[str]:
        """Extract the blob path from a GCS URL (handles both public and signed URLs)."""
        if not url:
            return None
        
        try:
            # Handle URLs like: 
            # - https://storage.googleapis.com/bucket-name/path/to/file.jpg
            # - https://storage.googleapis.com/bucket-name/path/to/file.jpg?Expires=...&Signature=...
            parsed = urlparse(url)
            if "storage.googleapis.com" in parsed.netloc:
                # Path is /bucket-name/path/to/file.jpg (query params are ignored by urlparse)
                path_parts = parsed.path.strip("/").split("/", 1)
                if len(path_parts) > 1:
                    return path_parts[1]  # Return path after bucket name
            return None
        except Exception as e:
            logger.warning(f"Failed to extract blob path from URL: {e}")
            return None
    
    @classmethod
    async def delete_file(cls, url: str) -> bool:
        """
        Delete a file from GCP Storage by its URL.
        
        Args:
            url: The public URL of the file to delete
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        blob_path = cls.extract_blob_path_from_url(url)
        if not blob_path:
            logger.warning(f"Could not extract blob path from URL: {url}")
            return False
        
        try:
            client = cls.get_client()
            bucket = client.bucket(settings.GCP_STORAGE_BUCKET_NAME)
            blob = bucket.blob(blob_path)
            blob.delete()
            logger.info(f"Successfully deleted file: {blob_path}")
            return True
        except NotFound:
            logger.warning(f"File not found for deletion: {blob_path}")
            return True  # Consider it successful if file doesn't exist
        except Exception as e:
            logger.error(f"Error deleting file {blob_path}: {e}")
            return False
    
    @classmethod
    async def upload_profile_picture(
        cls,
        file: UploadFile,
        user_id: str,
        old_profile_picture_url: Optional[str] = None
    ) -> str:
        """
        Upload profile picture to GCP Storage.
        Deletes the old profile picture if provided.
        
        Args:
            file: Uploaded file
            user_id: User ID for organizing files
            old_profile_picture_url: URL of existing profile picture to delete
        
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
                logger.warning(f"Could not verify bucket existence (may be permission issue): {str(check_error)}")
            
            blob = bucket.blob(unique_filename)
            
            # Set content type and cache control for better performance
            blob.content_type = "image/jpeg"
            blob.cache_control = "public, max-age=31536000"  # Cache for 1 year
            
            # Upload the file
            blob.upload_from_string(file_content, content_type="image/jpeg")
            
            # Generate a signed URL that works regardless of bucket-level access settings
            # The signed URL is valid for 7 days - after that, a new URL will be generated
            # when the user uploads a new picture or refreshes their session
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(days=7),  # 7 days expiry
                method="GET"
            )
            
            logger.info(f"Successfully uploaded profile picture with signed URL: {unique_filename}")
            
            # Delete old profile picture if provided (do this after successful upload)
            if old_profile_picture_url:
                deleted = await cls.delete_file(old_profile_picture_url)
                if deleted:
                    logger.info(f"Deleted old profile picture")
                else:
                    logger.warning(f"Could not delete old profile picture")
            
            return signed_url
            
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
    
    @classmethod
    async def upload_clinic_logo(
        cls,
        file: UploadFile,
        clinic_id: str,
        old_logo_url: Optional[str] = None
    ) -> str:
        """
        Upload clinic logo to GCP Storage.
        Deletes the old logo if provided.
        
        Args:
            file: Uploaded file
            clinic_id: Clinic ID for organizing files
            old_logo_url: URL of existing logo to delete
        
        Returns:
            str: Signed URL of uploaded file
        """
        # Validate file type
        allowed_types = ["image/jpeg", "image/jpg", "image/png"]
        if file.content_type not in allowed_types:
            raise BadRequestException(
                "Invalid file type. Only JPG and PNG images are allowed."
            )
        
        # Validate file size (2MB max for logos)
        file_content = await file.read()
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > 2:
            raise BadRequestException(
                "File size exceeds 2MB limit. Please upload a smaller image."
            )
        
        # Validate and optimize image
        try:
            image = Image.open(io.BytesIO(file_content))
            # Convert to RGB if necessary (handles RGBA, P, etc.)
            if image.mode in ("RGBA", "P"):
                rgb_image = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "RGBA":
                    rgb_image.paste(image, mask=image.split()[3])
                else:
                    rgb_image.paste(image)
                image = rgb_image
            
            # Resize if too large (max 512x512 for logos)
            max_size = 512
            if image.width > max_size or image.height > max_size:
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Convert to bytes
            output = io.BytesIO()
            image_format = "JPEG"
            image.save(output, format=image_format, quality=90, optimize=True)
            file_content = output.getvalue()
            
        except Exception as e:
            logger.error(f"Error processing logo image: {str(e)}")
            raise BadRequestException("Invalid image file. Please upload a valid image.")
        
        # Generate unique filename
        file_extension = "jpg"
        unique_filename = f"clinic-logos/{clinic_id}/{uuid.uuid4()}.{file_extension}"
        
        # Upload to GCP
        try:
            client = cls.get_client()
            bucket = client.bucket(settings.GCP_STORAGE_BUCKET_NAME)
            
            blob = bucket.blob(unique_filename)
            blob.content_type = "image/jpeg"
            blob.cache_control = "public, max-age=31536000"
            
            blob.upload_from_string(file_content, content_type="image/jpeg")
            
            # Generate signed URL
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(days=7),
                method="GET"
            )
            
            logger.info(f"Successfully uploaded clinic logo: {unique_filename}")
            
            # Delete old logo if provided
            if old_logo_url:
                deleted = await cls.delete_file(old_logo_url)
                if deleted:
                    logger.info(f"Deleted old clinic logo")
                else:
                    logger.warning(f"Could not delete old clinic logo")
            
            return signed_url
            
        except BadRequestException:
            raise
        except Exception as e:
            logger.error(f"Error uploading clinic logo to GCP: {str(e)}")
            error_message = str(e)
            if "403" in error_message or "permission" in error_message.lower():
                raise BadRequestException(
                    "Permission denied. Please check that the service account has Storage Admin role on the bucket."
                )
            elif "404" in error_message or "not found" in error_message.lower():
                raise BadRequestException(
                    f"Bucket '{settings.GCP_STORAGE_BUCKET_NAME}' not found."
                )
            else:
                raise BadRequestException(
                    f"Failed to upload logo to GCP: {error_message}"
                )
