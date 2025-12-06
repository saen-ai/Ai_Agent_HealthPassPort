"""Pydantic schemas for lab report extraction."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ExtractedBiomarker(BaseModel):
    """Schema for a single extracted biomarker."""
    name: str                           # Original name from report
    standardized_name: str              # Normalized name
    category: str                       # CBC, LIPID, etc.
    value: float
    unit: str
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    flag: Optional[str] = None          # HIGH, LOW, CRITICAL_HIGH, CRITICAL_LOW
    is_abnormal: bool = False


class LabReportResult(BaseModel):
    """Schema for the final extracted lab report result."""
    # Report metadata
    report_type: str = "OTHER"
    lab_name: Optional[str] = None
    report_date: Optional[str] = None
    
    # Extracted biomarkers
    biomarkers: List[ExtractedBiomarker] = Field(default_factory=list)
    
    # Summary
    total_biomarkers: int = 0
    abnormal_count: int = 0
    
    class Config:
        json_schema_extra = {
            "example": {
                "report_type": "CBC",
                "lab_name": "Aster Diagnostic",
                "report_date": "2024-01-15",
                "biomarkers": [
                    {
                        "name": "Hemoglobin",
                        "standardized_name": "hemoglobin",
                        "category": "CBC",
                        "value": 14.2,
                        "unit": "g/dL",
                        "reference_min": 13.5,
                        "reference_max": 17.5,
                        "flag": None,
                        "is_abnormal": False
                    }
                ],
                "total_biomarkers": 1,
                "abnormal_count": 0
            }
        }


class ProcessRequest(BaseModel):
    """Request to process a lab report."""
    patient_id: str
    clinic_id: str
    report_date: datetime
    pdf_password: Optional[str] = None


class ProcessResponse(BaseModel):
    """Response after initiating lab report processing."""
    status: str                         # "processing", "waiting_password", "completed", "failed"
    thread_id: str                      # For tracking/resuming
    report_id: Optional[str] = None
    message: str
    result: Optional[LabReportResult] = None


class ResumeRequest(BaseModel):
    """Request to resume processing with password."""
    password: str


class ResumeDateRequest(BaseModel):
    """Request to resume processing with report date."""
    report_date: str  # YYYY-MM-DD format


class BiomarkerHistoryResponse(BaseModel):
    """Response for biomarker history query."""
    patient_id: str
    biomarker_name: str
    category: str
    readings: List[dict]
    trend_direction: str
    trend_percent: float
    latest_value: float
    latest_unit: str
    latest_flag: Optional[str] = None


class LabReportListResponse(BaseModel):
    """Response for lab report list query."""
    reports: List[dict]
    total: int

