"""
Shared dependencies across the application.

This module contains dependency functions that can be used
across different features.
"""

from typing import Optional
from fastapi import Depends
from app.features.auth.models import User
from app.features.auth.dependencies import get_current_user


# Re-export commonly used dependencies
__all__ = ["get_current_user"]
