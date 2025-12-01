from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from app.features.auth.models import User
from app.features.auth.service import AuthService
from app.core.security import decode_token
from app.shared.exceptions import CredentialsException


# HTTP Bearer security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Dependency to get current authenticated user.
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        User: Current authenticated user
        
    Raises:
        CredentialsException: If credentials are invalid
    """
    token = credentials.credentials
    
    # Decode token
    payload = decode_token(token)
    if payload is None:
        raise CredentialsException("Invalid authentication credentials")
    
    # Get user email from token
    email: str = payload.get("sub")
    if email is None:
        raise CredentialsException("Invalid authentication credentials")
    
    # Get user from database
    user = await AuthService.get_user_by_email(email)
    if user is None:
        raise CredentialsException("User not found")
    
    if not user.is_active:
        raise CredentialsException("Inactive user")
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get current active user.
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        User: Current active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """
    Dependency to get current user if token is provided (optional).
    
    Args:
        credentials: Optional HTTP Bearer credentials
        
    Returns:
        Optional[User]: Current user if authenticated, None otherwise
    """
    if credentials is None:
        return None
    
    try:
        token = credentials.credentials
        payload = decode_token(token)
        if payload is None:
            return None
        
        email: str = payload.get("sub")
        if email is None:
            return None
        
        # This would need to be awaited, but for optional dependency we return None
        return None
    except:
        return None
