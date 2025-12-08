"""Lab Report document model."""

from datetime import datetime
from typing import Optional
from enum import Enum
from beanie import Document, Indexed
from pydantic import Field


class ReportStatus(str, Enum):
    """Status of lab report processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    WAITING_PASSWORD = "waiting_password"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportType(str, Enum):
    """Type of lab report."""
    CBC = "CBC"
    LIPID = "LIPID"
    METABOLIC = "METABOLIC"
    THYROID = "THYROID"
    LIVER = "LIVER"
    KIDNEY = "KIDNEY"
    VITAMIN = "VITAMIN"
    HORMONE = "HORMONE"
    OTHER = "OTHER"


class LabReport(Document):
    """Lab report document model."""
    
    # Patient and clinic association
    patient_id: Indexed(str)
    clinic_id: Indexed(str)
    
    # Report metadata
    report_date: datetime
    collection_date: Optional[datetime] = None
    lab_name: Optional[str] = None
    report_type: str = ReportType.OTHER.value
    
    # File storage (optional for images)
    pdf_url: Optional[str] = None
    
    # Processing status
    status: str = ReportStatus.PENDING.value
    thread_id: Optional[str] = None  # For LangGraph workflow tracking
    error_message: Optional[str] = None
    
    # Raw extraction data (for debugging/reprocessing)
    raw_text: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    
    class Settings:
        name = "lab_reports"
        indexes = [
            "patient_id",
            "clinic_id",
            "report_date",
            "status",
            [("patient_id", 1), ("report_date", -1)],  # Compound index
        ]

