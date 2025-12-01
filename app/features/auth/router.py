from fastapi import APIRouter, Depends, status
from app.features.auth.schemas import (
    SignupRequest,
    SignupResponse,
    LoginRequest,
    LoginResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
    MessageResponse,
    UserResponse,
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
        role=current_user.role,
        clinic_id=current_user.clinic_id,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )
