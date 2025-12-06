"""Biomarker document models."""

from datetime import datetime
from typing import Optional, List
from enum import Enum
from beanie import Document, Indexed
from pydantic import BaseModel, Field


class BiomarkerFlag(str, Enum):
    """Flag for abnormal biomarker values."""
    HIGH = "HIGH"
    LOW = "LOW"
    CRITICAL_HIGH = "CRITICAL_HIGH"
    CRITICAL_LOW = "CRITICAL_LOW"


class Biomarker(Document):
    """Individual biomarker reading from a lab report."""
    
    # Associations
    patient_id: Indexed(str)
    report_id: Indexed(str)
    clinic_id: Indexed(str)
    
    # Biomarker identification
    name: str                           # Original name from report (e.g., "Hemoglobin")
    standardized_name: Indexed(str)     # Normalized name (e.g., "hemoglobin")
    category: str                       # "CBC", "LIPID", etc.
    
    # Value
    value: float
    unit: str
    
    # Reference range
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    
    # Status
    flag: Optional[str] = None          # HIGH, LOW, CRITICAL_HIGH, CRITICAL_LOW
    is_abnormal: bool = False
    
    # Date of the test
    test_date: datetime
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "biomarkers"
        indexes = [
            "patient_id",
            "standardized_name",
            "test_date",
            "is_abnormal",
            [("patient_id", 1), ("standardized_name", 1)],  # For history queries
            [("patient_id", 1), ("test_date", -1)],          # For recent results
        ]


class BiomarkerReading(BaseModel):
    """Single reading in biomarker history."""
    date: datetime
    value: float
    unit: str
    flag: Optional[str] = None
    report_id: str


class BiomarkerTrend(Document):
    """Pre-computed trend data for fast dashboard queries."""
    
    # Unique identifier
    patient_id: Indexed(str)
    clinic_id: Indexed(str)
    biomarker_name: Indexed(str)        # standardized_name
    category: str
    
    # All readings (sorted by date, most recent last)
    readings: List[BiomarkerReading] = Field(default_factory=list)
    
    # Latest values (for quick access)
    latest_value: float
    latest_unit: str
    latest_date: datetime
    latest_flag: Optional[str] = None
    
    # Trend analysis
    trend_direction: str = "stable"     # "increasing", "decreasing", "stable"
    trend_percent: float = 0.0          # Percentage change from first to last
    
    # Statistics
    min_value: float
    max_value: float
    average_value: float
    reading_count: int = 0
    
    # Timestamps
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "biomarker_trends"
        indexes = [
            [("patient_id", 1), ("biomarker_name", 1)],  # Unique compound
        ]
    
    def add_reading(self, reading: BiomarkerReading):
        """Add a new reading and update statistics."""
        self.readings.append(reading)
        self.readings.sort(key=lambda r: r.date)
        
        # Update latest
        self.latest_value = reading.value
        self.latest_unit = reading.unit
        self.latest_date = reading.date
        self.latest_flag = reading.flag
        
        # Update statistics
        values = [r.value for r in self.readings]
        self.min_value = min(values)
        self.max_value = max(values)
        self.average_value = sum(values) / len(values)
        self.reading_count = len(self.readings)
        
        # Calculate trend
        if len(values) >= 2:
            first_value = values[0]
            last_value = values[-1]
            if first_value != 0:
                self.trend_percent = ((last_value - first_value) / first_value) * 100
                if self.trend_percent > 5:
                    self.trend_direction = "increasing"
                elif self.trend_percent < -5:
                    self.trend_direction = "decreasing"
                else:
                    self.trend_direction = "stable"
        
        self.updated_at = datetime.utcnow()

