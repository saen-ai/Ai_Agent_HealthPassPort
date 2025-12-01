from datetime import datetime, timedelta
from typing import Optional
from beanie import PydanticObjectId
from app.features.auth.models import User, PasswordReset
from app.features.auth.schemas import SignupRequest, LoginRequest, UserResponse
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    generate_reset_token
)
from app.core.email import send_password_reset_email, send_welcome_email
from app.shared.exceptions import (
    BadRequestException,
    NotFoundException,
    CredentialsException,
    ConflictException
)


class AuthService:
    """Authentication service for handling auth business logic."""
    
    @staticmethod
    async def signup(signup_data: SignupRequest) -> tuple[User, str, Optional[str]]:
        """
        Register a new user and create their clinic.
        
        Returns:
            tuple: (user, access_token, clinic_id)
        """
        # Check if user already exists
        existing_user = await User.find_one(User.email == signup_data.email)
        if existing_user:
            raise ConflictException("Email already registered")
        
        # Create user
        user = User(
            email=signup_data.email,
            password_hash=get_password_hash(signup_data.password),
            name=signup_data.name,
            role="admin",
        )
        await user.insert()
        
        # TODO: Create clinic when clinic feature is implemented
        # For now, we'll set clinic_id to None
        clinic_id = None
        
        # Create access token
        access_token = create_access_token(data={"sub": user.email, "user_id": str(user.id)})
        
        # Send welcome email (non-blocking)
        try:
            await send_welcome_email(user.email, user.name)
        except Exception as e:
            print(f"Failed to send welcome email: {str(e)}")
        
        return user, access_token, clinic_id
    
    @staticmethod
    async def login(login_data: LoginRequest) -> tuple[User, str]:
        """
        Authenticate user and return access token.
        
        Returns:
            tuple: (user, access_token)
        """
        # Find user by email
        user = await User.find_one(User.email == login_data.email)
        if not user:
            raise CredentialsException("Invalid email or password")
        
        # Verify password
        if not verify_password(login_data.password, user.password_hash):
            raise CredentialsException("Invalid email or password")
        
        # Check if user is active
        if not user.is_active:
            raise CredentialsException("Account is inactive")
        
        # Create access token
        access_token = create_access_token(data={"sub": user.email, "user_id": str(user.id)})
        
        return user, access_token
    
    @staticmethod
    async def forgot_password(email: str) -> bool:
        """
        Generate password reset token and send email.
        
        Returns:
            bool: True if email sent successfully
        """
        # Find user by email
        user = await User.find_one(User.email == email)
        if not user:
            # Don't reveal if email exists or not for security
            return True
        
        # Generate reset token
        token = generate_reset_token()
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Save reset token
        password_reset = PasswordReset(
            user_id=str(user.id),
            email=email,
            token=token,
            expires_at=expires_at,
        )
        await password_reset.insert()
        
        # Send reset email
        try:
            await send_password_reset_email(email, token)
            return True
        except Exception as e:
            print(f"Failed to send password reset email: {str(e)}")
            return False
    
    @staticmethod
    async def reset_password(token: str, new_password: str) -> bool:
        """
        Reset user password using token.
        
        Returns:
            bool: True if password reset successfully
        """
        # Find reset token
        password_reset = await PasswordReset.find_one(
            PasswordReset.token == token,
            PasswordReset.used == False
        )
        
        if not password_reset:
            raise BadRequestException("Invalid or expired reset token")
        
        # Check if token is expired
        if password_reset.expires_at < datetime.utcnow():
            raise BadRequestException("Reset token has expired")
        
        # Find user
        user = await User.get(PydanticObjectId(password_reset.user_id))
        if not user:
            raise NotFoundException("User not found")
        
        # Update password
        user.password_hash = get_password_hash(new_password)
        await user.save()
        
        # Mark token as used
        password_reset.used = True
        await password_reset.save()
        
        return True
    
    @staticmethod
    async def change_password(user: User, current_password: str, new_password: str) -> bool:
        """
        Change user password.
        
        Returns:
            bool: True if password changed successfully
        """
        # Verify current password
        if not verify_password(current_password, user.password_hash):
            raise BadRequestException("Current password is incorrect")
        
        # Update password
        user.password_hash = get_password_hash(new_password)
        await user.save()
        
        return True
    
    @staticmethod
    async def get_user_by_email(email: str) -> Optional[User]:
        """Get user by email."""
        return await User.find_one(User.email == email)
    
    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            return await User.get(PydanticObjectId(user_id))
        except:
            return None
