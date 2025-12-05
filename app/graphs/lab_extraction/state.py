"""LangGraph state schema for lab extraction workflow."""

from typing import TypedDict, Annotated, Optional, List
from operator import add


class LabExtractionState(TypedDict):
    """State schema for the lab extraction workflow."""
    
    # Input - provided when starting the workflow
    pdf_path: str
    patient_id: str
    clinic_id: str
    thread_id: str
    report_date: str  # ISO format date
    
    # Encryption handling
    is_encrypted: bool
    password: Optional[str]
    decrypt_error: Optional[str]
    
    # Text extraction results
    extracted_text: str
    extracted_tables: List[List[List[str]]]
    
    # Vision extraction
    needs_vision: bool
    image_paths: List[str]
    vision_data: dict
    
    # Combined data for agent
    combined_data: str
    
    # Agent output
    report_type: str
    lab_name: Optional[str]
    biomarkers: List[dict]
    
    # Processing results
    report_id: Optional[str]
    status: str  # "processing", "waiting_password", "completed", "failed"
    
    # Errors (using add operator to accumulate errors)
    errors: Annotated[List[str], add]

