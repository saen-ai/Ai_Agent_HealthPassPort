from fastapi import APIRouter, Depends, status
from app.features.auth.schemas import (
    SignupRequest,
    SignupResponse,
    LoginRequest,
    LoginResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
    UpdateProfileRequest,
    MessageResponse,
    UserResponse,
    SendSignupOtpRequest,
    VerifySignupOtpRequest,
    SendLoginOtpRequest,
    VerifyLoginOtpRequest,
)
from app.features.auth.service import AuthService
from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(signup_data: SignupRequest):
    """
    Register a new user and create their clinic.
    
    - **name**: User's full name
    - **email**: User's email address
    - **password**: Strong password (min 8 chars, 1 uppercase, 1 lowercase, 1 digit)
    - **clinic_name**: Name of the clinic to create
    """
    user, access_token, clinic_id = await AuthService.signup(signup_data)
    
    return SignupResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            phone=user.phone,
            specialization=user.specialization,
            role=user.role,
            clinic_id=clinic_id,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
        clinic_id=clinic_id,
    )


@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    """
    Authenticate user and return access token.
    
    - **email**: User's email address
    - **password**: User's password
    """
    user, access_token = await AuthService.login(login_data)
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            phone=user.phone,
            specialization=user.specialization,
            role=user.role,
            clinic_id=user.clinic_id,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
    )


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(request: ForgotPasswordRequest):
    """
    Send password reset email to user.
    
    - **email**: User's email address
    """
    await AuthService.forgot_password(request.email)
    
    return MessageResponse(
        message="If the email exists, a password reset link has been sent"
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(request: ResetPasswordRequest):
    """
    Reset user password using token from email.
    
    - **token**: Password reset token from email
    - **new_password**: New password (min 8 chars, 1 uppercase, 1 lowercase, 1 digit)
    """
    await AuthService.reset_password(request.token, request.new_password)
    
    return MessageResponse(message="Password reset successfully")


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Change current user's password.
    
    Requires authentication.
    
    - **current_password**: Current password
    - **new_password**: New password (min 8 chars)
    """
    await AuthService.change_password(
        current_user,
        request.current_password,
        request.new_password
    )
    
    return MessageResponse(message="Password changed successfully")


@router.post("/logout", response_model=MessageResponse)
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout current user.
    
    Requires authentication.
    
    Note: With JWT tokens, logout is handled client-side by removing the token.
    This endpoint is provided for consistency and future session management.
    """
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's information.
    
    Requires authentication.
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        phone=current_user.phone,
        specialization=current_user.specialization,
        role=current_user.role,
        clinic_id=current_user.clinic_id,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    update_data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update current user's profile information.
    
    Requires authentication.
    
    - **name**: User's full name (optional)
    - **phone**: User's phone number (optional)
    - **specialization**: User's specialization (optional)
    """
    # Convert Pydantic model to dict, excluding None values
    update_dict = update_data.model_dump(exclude_unset=True)
    
    # Update user profile
    updated_user = await AuthService.update_profile(current_user, update_dict)
    
    return UserResponse(
        id=str(updated_user.id),
        email=updated_user.email,
        name=updated_user.name,
        phone=updated_user.phone,
        specialization=updated_user.specialization,
        role=updated_user.role,
        clinic_id=updated_user.clinic_id,
        is_active=updated_user.is_active,
        is_verified=updated_user.is_verified,
        created_at=updated_user.created_at,
        updated_at=updated_user.updated_at,
    )


@router.post("/send-signup-otp", response_model=MessageResponse)
async def send_signup_otp(request: SendSignupOtpRequest):
    """
    Send OTP code for signup verification.
    
    - **email**: User's email address
    - **name**: User's full name
    - **clinic_name**: Name of the clinic to create
    - **password**: Strong password (min 8 chars, 1 uppercase, 1 lowercase, 1 digit)
    - **phone**: Optional phone number
    """
    await AuthService.send_signup_otp(request)
    
    return MessageResponse(
        message="OTP code has been sent to your email"
    )


@router.post("/verify-signup-otp", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def verify_signup_otp(request: VerifySignupOtpRequest):
    """
    Verify OTP code and create user account with clinic.
    
    - **email**: User's email address
    - **otp_code**: 4-digit OTP code from email
    - **name**: User's full name
    - **clinic_name**: Name of the clinic to create
    - **password**: Strong password (min 8 chars, 1 uppercase, 1 lowercase, 1 digit)
    - **phone**: Optional phone number
    """
    from app.core.logging import logger
    logger.info(f"📥 Received verify-signup-otp request for {request.email}")
    try:
        user, access_token, clinic_id = await AuthService.verify_signup_otp(request)
        logger.info(f"✅ Successfully verified OTP and created user for {request.email}")
    except Exception as e:
        logger.error(f"❌ Error in verify_signup_otp: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    
    return SignupResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            phone=user.phone,
            specialization=user.specialization,
            role=user.role,
            clinic_id=clinic_id,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
        clinic_id=clinic_id,
    )


@router.post("/send-login-otp", response_model=MessageResponse)
async def send_login_otp(request: SendLoginOtpRequest):
    """
    Send OTP code for login verification.
    
    - **email**: User's email address
    """
    await AuthService.send_login_otp(request)
    
    return MessageResponse(
        message="OTP code has been sent to your email"
    )


@router.post("/verify-login-otp", response_model=LoginResponse)
async def verify_login_otp(request: VerifyLoginOtpRequest):
    """
    Verify OTP code and authenticate user.
    
    - **email**: User's email address
    - **otp_code**: 4-digit OTP code from email
    """
    user, access_token = await AuthService.verify_login_otp(request)
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            phone=user.phone,
            specialization=user.specialization,
            role=user.role,
            clinic_id=user.clinic_id,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
    )
