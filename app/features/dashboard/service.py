# Dashboard Feature - Service

from typing import List, Tuple
from datetime import datetime, timedelta
from bson import ObjectId

from app.features.dashboard.schemas import (
    DashboardStatsResponse,
    ActivityItem,
    RecentActivityResponse,
)
from app.features.patients.models import Patient
from app.features.messages.models import Conversation, Message
from app.features.notes.models import Note
from app.core.logging import logger


class DashboardService:
    """Service for dashboard statistics and activity."""
    
    @staticmethod
    async def get_dashboard_stats(clinic_id: str) -> DashboardStatsResponse:
        """
        Get dashboard statistics for a clinic.
        
        Args:
            clinic_id: The clinic ID
            
        Returns:
            DashboardStatsResponse with aggregated statistics
        """
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        two_weeks_ago = now - timedelta(days=14)
        
        # Total patients
        total_patients = await Patient.find(
            Patient.clinic_id == clinic_id
        ).count()
        
        # Active patients
        active_patients = await Patient.find(
            Patient.clinic_id == clinic_id,
            Patient.is_active == True
        ).count()
        
        # Unread messages (sum of doctor_unread_count across all conversations)
        conversations = await Conversation.find(
            Conversation.clinic_id == clinic_id,
            Conversation.is_active == True
        ).to_list()
        
        unread_messages = sum(conv.doctor_unread_count for conv in conversations)
        
        # Notes this week
        notes_this_week = await Note.find(
            Note.clinic_id == clinic_id,
            Note.is_deleted == False,
            Note.created_at >= week_ago
        ).count()
        
        # New patients this week
        new_patients_this_week = await Patient.find(
            Patient.clinic_id == clinic_id,
            Patient.created_at >= week_ago
        ).count()
        
        # New patients last week (for change calculation)
        new_patients_last_week = await Patient.find(
            Patient.clinic_id == clinic_id,
            Patient.created_at >= two_weeks_ago,
            Patient.created_at < week_ago
        ).count()
        
        # Calculate change percent
        patient_change_percent = None
        if new_patients_last_week > 0:
            patient_change_percent = ((new_patients_this_week - new_patients_last_week) / new_patients_last_week) * 100
        elif new_patients_this_week > 0:
            patient_change_percent = 100.0
        
        return DashboardStatsResponse(
            total_patients=total_patients,
            active_patients=active_patients,
            unread_messages=unread_messages,
            notes_this_week=notes_this_week,
            new_patients_this_week=new_patients_this_week,
            patient_change_percent=patient_change_percent,
        )
    
    @staticmethod
    async def get_recent_activity(
        clinic_id: str,
        limit: int = 10
    ) -> RecentActivityResponse:
        """
        Get recent activity for a clinic dashboard.
        
        Combines:
        - New patients added
        - Recent messages received
        - Recent notes created
        
        Args:
            clinic_id: The clinic ID
            limit: Maximum number of activities to return
            
        Returns:
            RecentActivityResponse with combined activities
        """
        activities: List[ActivityItem] = []
        
        # Get recent patients (last 7 days)
        recent_patients = await Patient.find(
            Patient.clinic_id == clinic_id
        ).sort([("created_at", -1)]).limit(limit).to_list()
        
        for patient in recent_patients:
            activities.append(ActivityItem(
                id=f"patient_{patient.patient_id}",
                type="patient",
                title=patient.name,
                description="New patient registered",
                patient_id=patient.patient_id,
                patient_name=patient.name,
                timestamp=patient.created_at,
            ))
        
        # Get recent messages (last 7 days)
        # Find conversations for this clinic
        conversations = await Conversation.find(
            Conversation.clinic_id == clinic_id,
            Conversation.is_active == True
        ).to_list()
        
        conversation_ids = [str(conv.id) for conv in conversations]
        
        # Get recent messages from patients
        if conversation_ids:
            recent_messages = await Message.find(
                Message.is_deleted == False,
                Message.sender_type == "patient"  # Only patient messages
            ).sort([("created_at", -1)]).limit(limit * 2).to_list()
            
            # Filter to only conversations belonging to this clinic
            for msg in recent_messages:
                if msg.conversation_id in conversation_ids:
                    # Get patient info from conversation
                    conv = next((c for c in conversations if str(c.id) == msg.conversation_id), None)
                    if conv:
                        # Get patient name
                        patient = await Patient.find_one(Patient.patient_id == conv.patient_id)
                        patient_name = patient.name if patient else "Unknown Patient"
                        
                        activities.append(ActivityItem(
                            id=f"message_{msg.id}",
                            type="message",
                            title=patient_name,
                            description="Sent a message",
                            patient_id=conv.patient_id,
                            patient_name=patient_name,
                            timestamp=msg.created_at,
                        ))
                        
                        if len(activities) >= limit * 3:
                            break
        
        # Get recent notes (last 7 days)
        recent_notes = await Note.find(
            Note.clinic_id == clinic_id,
            Note.is_deleted == False
        ).sort([("created_at", -1)]).limit(limit).to_list()
        
        for note in recent_notes:
            # Get patient name
            patient = await Patient.find_one(Patient.patient_id == note.patient_id)
            patient_name = patient.name if patient else "Unknown Patient"
            
            activities.append(ActivityItem(
                id=f"note_{note.id}",
                type="note",
                title=patient_name,
                description=f"Visit note: {note.title}",
                patient_id=note.patient_id,
                patient_name=patient_name,
                timestamp=note.created_at,
            ))
        
        # Sort all activities by timestamp descending
        activities.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Limit to requested count
        activities = activities[:limit]
        
        return RecentActivityResponse(
            activities=activities,
            total=len(activities),
        )

