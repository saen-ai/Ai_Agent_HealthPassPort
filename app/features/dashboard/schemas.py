# Dashboard Feature - Schemas

from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


# ============== Dashboard Statistics ==============

class StatItem(BaseModel):
    """A single dashboard statistic."""
    name: str
    value: str
    change: Optional[str] = None
    change_type: Literal["positive", "negative", "neutral"] = "neutral"


class DashboardStatsResponse(BaseModel):
    """Response schema for dashboard statistics."""
    total_patients: int
    active_patients: int
    unread_messages: int
    notes_this_week: int
    new_patients_this_week: int
    # Calculated changes
    patient_change_percent: Optional[float] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_patients": 284,
                "active_patients": 280,
                "unread_messages": 9,
                "notes_this_week": 12,
                "new_patients_this_week": 5,
                "patient_change_percent": 12.0
            }
        }


# ============== Recent Activity ==============

class ActivityItem(BaseModel):
    """A single activity item."""
    id: str
    type: Literal["patient", "message", "note"]
    title: str
    description: str
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    timestamp: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "act_123",
                "type": "patient",
                "title": "Sarah Johnson",
                "description": "New patient registered",
                "patient_id": "P00001",
                "patient_name": "Sarah Johnson",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class RecentActivityResponse(BaseModel):
    """Response schema for recent activity."""
    activities: List[ActivityItem]
    total: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "activities": [
                    {
                        "id": "act_1",
                        "type": "note",
                        "title": "Michael Chen",
                        "description": "Visit note added",
                        "patient_id": "P00002",
                        "patient_name": "Michael Chen",
                        "timestamp": "2024-01-15T10:30:00Z"
                    }
                ],
                "total": 1
            }
        }

