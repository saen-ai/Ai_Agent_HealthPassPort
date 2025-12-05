# Dashboard Feature - Router

from fastapi import APIRouter, Depends, Query
from app.features.auth.models import User
from app.features.auth.dependencies import get_current_user
from app.features.dashboard.schemas import (
    DashboardStatsResponse,
    RecentActivityResponse,
)
from app.features.dashboard.service import DashboardService


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get dashboard statistics for the current user's clinic.
    
    Returns:
    - Total patients
    - Active patients
    - Unread messages count
    - Notes created this week
    - New patients this week
    - Patient change percentage
    
    Requires authentication.
    """
    return await DashboardService.get_dashboard_stats(
        clinic_id=current_user.clinic_id
    )


@router.get("/activity", response_model=RecentActivityResponse)
async def get_recent_activity(
    limit: int = Query(10, ge=1, le=50, description="Number of activities to return"),
    current_user: User = Depends(get_current_user)
):
    """
    Get recent activity for the current user's clinic dashboard.
    
    Returns combined activity from:
    - New patients registered
    - Messages received from patients
    - Notes created
    
    Activities are sorted by timestamp (most recent first).
    
    Requires authentication.
    """
    return await DashboardService.get_recent_activity(
        clinic_id=current_user.clinic_id,
        limit=limit
    )

