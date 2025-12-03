from datetime import datetime, timedelta
from typing import Optional
from beanie import PydanticObjectId
from beanie.operators import And
from app.features.auth.models import User, PasswordReset, EmailVerification
from app.features.clinic.models import Clinic
from app.features.auth.schemas import (
    SignupRequest, LoginRequest, UserResponse, 
    SendSignupOtpRequest, VerifySignupOtpRequest,
    SendLoginOtpRequest, VerifyLoginOtpRequest
)
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    generate_reset_token,
    generate_otp
)
from app.core.email import send_password_reset_email, send_welcome_email, send_otp_email
from app.shared.exceptions import (
    BadRequestException,
    NotFoundException,
    CredentialsException,
    ConflictException
)
from app.core.logging import logger


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
        
        # Create clinic first
        clinic = Clinic(
            name=signup_data.clinic_name,
            address="",
            logo_url="",
            color_theme="#4F46E5"
        )
        await clinic.insert()
        
        # Create user
        user = User(
            email=signup_data.email,
            password_hash=get_password_hash(signup_data.password),
            name=signup_data.name,
            role="admin",
            clinic_id=str(clinic.id),
            is_verified=True
        )
        await user.insert()
        
        clinic_id = str(clinic.id)
        
        # Create access token
        access_token = create_access_token(data={"sub": user.email, "user_id": str(user.id)})
        
        # Send welcome email (non-blocking)
        try:
            logger.info(f"📧 Sending welcome email to {user.email}")
            await send_welcome_email(user.email, user.name)
            logger.info(f"✅ Welcome email sent to {user.email}")
        except Exception as e:
            logger.error(f"❌ Failed to send welcome email to {user.email}: {str(e)}")
        
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
            logger.info(f"📧 Sending password reset email to {email}")
            await send_password_reset_email(email, token)
            logger.info(f"✅ Password reset email sent to {email}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send password reset email to {email}: {str(e)}")
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
    async def update_profile(user: User, update_data: dict) -> User:
        """
        Update user profile information.
        
        Args:
            user: User document to update
            update_data: Dictionary with fields to update (name, phone, specialization)
        
        Returns:
            User: Updated user document
        """
        # Update only provided fields
        if "name" in update_data and update_data["name"] is not None:
            user.name = update_data["name"]
        if "phone" in update_data:
            user.phone = update_data["phone"]
        if "specialization" in update_data:
            user.specialization = update_data["specialization"]
        
        await user.save()
        return user
    
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
    
    @staticmethod
    async def send_signup_otp(request: SendSignupOtpRequest) -> bool:
        """
        Send OTP for signup verification.
        
        Returns:
            bool: True if OTP sent successfully
        """
        # Check if user already exists
        existing_user = await User.find_one(User.email == request.email)
        if existing_user:
            raise ConflictException("Email already registered")
        
        # Generate OTP
        otp_code = generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        
        # Invalidate any existing OTPs for this email
        existing_verifications = await EmailVerification.find(
            And(
                EmailVerification.email == request.email,
                EmailVerification.purpose == "signup",
                EmailVerification.used == False
            )
        ).to_list()
        
        for verification in existing_verifications:
            verification.used = True
            await verification.save()
        
        # Create new email verification
        email_verification = EmailVerification(
            email=request.email,
            otp_code=otp_code,
            expires_at=expires_at,
            purpose="signup"
        )
        await email_verification.insert()
        
        # Send OTP email
        logger.info(f"📧 Sending OTP code to {request.email} for signup")
        logger.info(f"   Generated OTP: {otp_code}")
        email_sent = await send_otp_email(request.email, otp_code, "signup")
        if not email_sent:
            logger.error(f"❌ Failed to send OTP email to {request.email}")
            logger.error("   Check backend logs above for SMTP error details")
            raise BadRequestException("Failed to send OTP email. Please check your email address and try again.")
        
        logger.info(f"✅ OTP code {otp_code} sent successfully to {request.email}")
        return True
    
    @staticmethod
    async def verify_signup_otp(request: VerifySignupOtpRequest) -> tuple[User, str, str]:
        """
        Verify OTP and create user account with clinic.
        
        Returns:
            tuple: (user, access_token, clinic_id)
        """
        logger.info(f"🔍 Verifying OTP for {request.email}")
        logger.info(f"   OTP code provided: {request.otp_code}")
        
        # Find all email verifications for this email (for debugging)
        all_verifications = await EmailVerification.find(
            EmailVerification.email == request.email
        ).to_list()
        logger.info(f"   Found {len(all_verifications)} verification(s) for this email")
        for v in all_verifications:
            logger.info(f"   - OTP: {v.otp_code}, Purpose: {v.purpose}, Used: {v.used}, Expires: {v.expires_at}")
        
        # Find email verification
        email_verification = await EmailVerification.find_one(
            And(
                EmailVerification.email == request.email,
                EmailVerification.otp_code == request.otp_code,
                EmailVerification.purpose == "signup",
                EmailVerification.used == False
            )
        )
        
        if not email_verification:
            logger.error(f"❌ No matching OTP found for {request.email}")
            logger.error(f"   Looking for: code={request.otp_code}, purpose=signup, used=False")
            raise BadRequestException("Invalid or expired OTP code")
        
        # Check if OTP is expired
        if email_verification.expires_at < datetime.utcnow():
            logger.error(f"❌ OTP expired for {request.email}")
            logger.error(f"   Expires at: {email_verification.expires_at}, Now: {datetime.utcnow()}")
            raise BadRequestException("OTP code has expired")
        
        logger.info(f"✅ OTP verified successfully for {request.email}")
        
        # Check if user already exists (race condition check)
        existing_user = await User.find_one(User.email == request.email)
        if existing_user:
            raise ConflictException("Email already registered")
        
        # Create clinic
        clinic = Clinic(
            name=request.clinic_name,
            address="",
            logo_url="",
            color_theme="#4F46E5"
        )
        await clinic.insert()
        
        # Create user
        user = User(
            email=request.email,
            password_hash=get_password_hash(request.password),
            name=request.name,
            phone=request.phone,
            role="admin",
            clinic_id=str(clinic.id),
            is_verified=True
        )
        await user.insert()
        
        # Mark OTP as used
        email_verification.used = True
        await email_verification.save()
        
        # Create access token
        access_token = create_access_token(data={"sub": user.email, "user_id": str(user.id)})
        
        # Send welcome email (non-blocking)
        try:
            logger.info(f"📧 Sending welcome email to {user.email}")
            await send_welcome_email(user.email, user.name)
            logger.info(f"✅ Welcome email sent to {user.email}")
        except Exception as e:
            logger.error(f"❌ Failed to send welcome email to {user.email}: {str(e)}")
        
        return user, access_token, str(clinic.id)
    
    @staticmethod
    async def send_login_otp(request: SendLoginOtpRequest) -> bool:
        """
        Send OTP for login verification.
        
        Returns:
            bool: True if OTP sent successfully
        """
        # Check if user exists
        user = await User.find_one(User.email == request.email)
        if not user:
            raise NotFoundException("No account found with this email")
        
        # Check if user is active
        if not user.is_active:
            raise BadRequestException("Account is inactive")
        
        # Generate OTP
        otp_code = generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        
        # Invalidate any existing OTPs for this email
        existing_verifications = await EmailVerification.find(
            And(
                EmailVerification.email == request.email,
                EmailVerification.purpose == "login",
                EmailVerification.used == False
            )
        ).to_list()
        
        for verification in existing_verifications:
            verification.used = True
            await verification.save()
        
        # Create new email verification
        email_verification = EmailVerification(
            email=request.email,
            otp_code=otp_code,
            expires_at=expires_at,
            purpose="login"
        )
        await email_verification.insert()
        
        # Send OTP email
        logger.info(f"📧 Sending OTP code to {request.email} for login")
        email_sent = await send_otp_email(request.email, otp_code, "login")
        if not email_sent:
            logger.error(f"❌ Failed to send OTP email to {request.email}")
            raise BadRequestException("Failed to send OTP email. Please try again.")
        
        logger.info(f"✅ OTP code sent successfully to {request.email}")
        return True
    
    @staticmethod
    async def verify_login_otp(request: VerifyLoginOtpRequest) -> tuple[User, str]:
        """
        Verify OTP and authenticate user.
        
        Returns:
            tuple: (user, access_token)
        """
        # Find email verification
        email_verification = await EmailVerification.find_one(
            And(
                EmailVerification.email == request.email,
                EmailVerification.otp_code == request.otp_code,
                EmailVerification.purpose == "login",
                EmailVerification.used == False
            )
        )
        
        if not email_verification:
            raise BadRequestException("Invalid or expired OTP code")
        
        # Check if OTP is expired
        if email_verification.expires_at < datetime.utcnow():
            raise BadRequestException("OTP code has expired")
        
        # Find user
        user = await User.find_one(User.email == request.email)
        if not user:
            raise NotFoundException("User not found")
        
        # Check if user is active
        if not user.is_active:
            raise BadRequestException("Account is inactive")
        
        # Mark OTP as used
        email_verification.used = True
        await email_verification.save()
        
        # Create access token
        access_token = create_access_token(data={"sub": user.email, "user_id": str(user.id)})
        
        return user, access_token
