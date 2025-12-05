"""LangGraph nodes for lab extraction workflow."""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from langgraph.types import interrupt
from pydantic import BaseModel, Field

from app.config import settings
from app.core.logging import logger
from app.services.pdf_service import PDFService
from app.services.vision_service import VisionService
from app.data.biomarker_mapping import (
    standardize_biomarker_name,
    get_biomarker_category,
    get_flag,
)
from app.models.lab_report import LabReport, ReportStatus
from app.models.biomarker import Biomarker, BiomarkerTrend, BiomarkerReading
from app.graphs.lab_extraction.state import LabExtractionState


# ============ STRUCTURED OUTPUT SCHEMA FOR AGENT ============

class ExtractedBiomarkerSchema(BaseModel):
    """Schema for extracted biomarker."""
    name: str = Field(description="Original name from report")
    value: float = Field(description="Numeric value")
    unit: str = Field(description="Unit of measurement")
    reference_min: float | None = Field(default=None, description="Minimum reference value")
    reference_max: float | None = Field(default=None, description="Maximum reference value")


class LabReportExtractionSchema(BaseModel):
    """Schema for the agent's structured output."""
    report_type: str = Field(description="Type of report: CBC, LIPID, METABOLIC, THYROID, LIVER, KIDNEY, VITAMIN, HORMONE, or OTHER")
    lab_name: str | None = Field(default=None, description="Name of the laboratory")
    biomarkers: list[ExtractedBiomarkerSchema] = Field(default_factory=list, description="List of extracted biomarkers")


# ============ NODE 1: RECEIVE UPLOAD ============

def receive_upload(state: LabExtractionState) -> dict:
    """
    Validate the uploaded PDF file.
    """
    logger.info(f"Receiving upload for patient {state['patient_id']}")
    
    pdf_path = state["pdf_path"]
    
    # Check if file exists
    if not os.path.exists(pdf_path):
        return {
            "errors": [f"PDF file not found: {pdf_path}"],
            "status": "failed"
        }
    
    # Get page count
    page_count = PDFService.get_page_count(pdf_path)
    if page_count == 0:
        return {
            "errors": ["Invalid PDF file or no pages found"],
            "status": "failed"
        }
    
    logger.info(f"PDF validated: {page_count} pages")
    return {"status": "processing"}


# ============ NODE 2: CHECK ENCRYPTION ============

def check_encryption(state: LabExtractionState) -> dict:
    """
    Check if the PDF is encrypted.
    """
    pdf_path = state["pdf_path"]
    is_encrypted = PDFService.check_encryption(pdf_path)
    
    logger.info(f"PDF encryption check: {is_encrypted}")
    return {"is_encrypted": is_encrypted}


# ============ NODE 3: REQUEST PASSWORD (Human-in-the-loop) ============

def request_password(state: LabExtractionState) -> dict:
    """
    Pause execution and ask for password using interrupt().
    """
    logger.info("PDF is encrypted, requesting password from user")
    
    # This will pause the workflow and return to the caller
    password = interrupt({
        "type": "password_required",
        "message": "This PDF is password-protected. Please provide the password.",
        "hint": "Tip: Lab passwords are often your date of birth (MMDDYYYY or DDMMYYYY)",
        "patient_id": state["patient_id"],
        "thread_id": state["thread_id"],
    })
    
    return {
        "password": password,
        "status": "processing"
    }


# ============ NODE 4: DECRYPT PDF ============

def decrypt_pdf(state: LabExtractionState) -> dict:
    """
    Attempt to decrypt the PDF with the provided password.
    """
    pdf_path = state["pdf_path"]
    password = state.get("password")
    
    if not password:
        return {
            "decrypt_error": "No password provided",
            "status": "waiting_password"
        }
    
    success, error = PDFService.decrypt_pdf(pdf_path, password)
    
    if success:
        logger.info("PDF decrypted successfully")
        return {"decrypt_error": None}
    else:
        logger.warning(f"Decryption failed: {error}")
        return {
            "decrypt_error": error,
            "errors": [f"Decryption failed: {error}"]
        }


# ============ NODE 5: EXTRACT TEXT ============

def extract_text(state: LabExtractionState) -> dict:
    """
    Extract text and tables from PDF using PyMuPDF and pdfplumber.
    """
    pdf_path = state["pdf_path"]
    password = state.get("password")
    
    logger.info("Extracting text from PDF")
    
    # Extract text
    text = PDFService.extract_text(pdf_path, password)
    
    # Extract tables
    tables = PDFService.extract_tables(pdf_path, password)
    
    # Check if we need vision (scanned PDF or too little text)
    needs_vision = len(text.strip()) < 100 or PDFService.has_images_or_scanned(pdf_path, password)
    
    logger.info(f"Text extracted: {len(text)} chars, needs_vision: {needs_vision}")
    
    return {
        "extracted_text": text,
        "extracted_tables": tables,
        "needs_vision": needs_vision,
    }


# ============ NODE 6: VISION EXTRACTION ============

def vision_extraction(state: LabExtractionState) -> dict:
    """
    Extract data from PDF images using GPT-4o Vision API.
    Only called if needs_vision is True.
    """
    if not state.get("needs_vision"):
        return {"vision_data": {}}
    
    pdf_path = state["pdf_path"]
    password = state.get("password")
    
    logger.info("Using Vision API for extraction")
    
    # Convert PDF to images
    output_dir = str(Path(settings.UPLOAD_DIR) / state["thread_id"])
    image_paths = PDFService.pdf_to_images(pdf_path, output_dir, password)
    
    if not image_paths:
        return {
            "errors": ["Failed to convert PDF to images"],
            "vision_data": {},
            "image_paths": []
        }
    
    # Extract using Vision API
    vision_service = VisionService()
    vision_data = vision_service.extract_from_multiple_images(image_paths)
    
    logger.info(f"Vision extracted {len(vision_data.get('biomarkers', []))} biomarkers")
    
    return {
        "vision_data": vision_data,
        "image_paths": image_paths
    }


# ============ NODE 7: COLLECT DATA ============

def collect_data(state: LabExtractionState) -> dict:
    """
    Merge text extraction and vision extraction results.
    """
    logger.info("Collecting and merging extracted data")
    
    combined = []
    
    # Add text extraction
    if state.get("extracted_text"):
        combined.append("=== TEXT EXTRACTION ===")
        combined.append(state["extracted_text"])
    
    # Add table data
    if state.get("extracted_tables"):
        combined.append("\n=== TABLES ===")
        for i, table in enumerate(state["extracted_tables"]):
            combined.append(f"\nTable {i+1}:")
            for row in table:
                combined.append(" | ".join([str(cell) if cell else "" for cell in row]))
    
    # Add vision data
    if state.get("vision_data") and state["vision_data"].get("biomarkers"):
        combined.append("\n=== VISION EXTRACTION ===")
        combined.append(json.dumps(state["vision_data"], indent=2))
    
    combined_text = "\n".join(combined)
    logger.info(f"Combined data: {len(combined_text)} chars")
    
    return {"combined_data": combined_text}


# ============ NODE 8: STANDARDIZE AGENT ============

async def standardize_agent(state: LabExtractionState) -> dict:
    """
    Use create_agent to classify report and extract/standardize biomarkers.
    """
    combined_data = state.get("combined_data", "")
    
    if not combined_data.strip():
        return {
            "errors": ["No data to process"],
            "status": "failed",
            "biomarkers": [],
            "report_type": "OTHER"
        }
    
    logger.info("Running standardization agent")
    
    # If we already have vision data with biomarkers, use that directly
    vision_data = state.get("vision_data", {})
    if vision_data.get("biomarkers"):
        biomarkers = []
        for bio in vision_data["biomarkers"]:
            std_name = standardize_biomarker_name(bio.get("name", ""))
            category = get_biomarker_category(std_name)
            flag = get_flag(std_name, bio.get("value", 0))
            
            biomarkers.append({
                "name": bio.get("name", ""),
                "standardized_name": std_name,
                "category": category,
                "value": bio.get("value", 0),
                "unit": bio.get("unit", ""),
                "reference_min": bio.get("reference_min"),
                "reference_max": bio.get("reference_max"),
                "flag": flag or bio.get("flag"),
                "is_abnormal": flag is not None or bio.get("flag") is not None,
            })
        
        return {
            "biomarkers": biomarkers,
            "report_type": vision_data.get("report_type", "OTHER"),
            "lab_name": vision_data.get("lab_name"),
        }
    
    # Otherwise, use agent to extract from text
    try:
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(model="gpt-4o", api_key=settings.OPENAI_API_KEY)
        
        system_prompt = """You are a medical lab report extraction expert.

Given raw text from a lab report, you must:
1. Identify the report type (CBC, LIPID, METABOLIC, THYROID, LIVER, KIDNEY, VITAMIN, HORMONE, or OTHER)
2. Extract ALL biomarkers/test results with their values, units, and reference ranges
3. Identify the laboratory name if present

Look for patterns like:
- "Test Name: Value Unit (Reference: min - max)"
- Tables with columns for Test, Result, Unit, Reference
- Any numerical health measurements

Return structured data with all biomarkers found."""

        structured_llm = llm.with_structured_output(LabReportExtractionSchema)
        
        result = structured_llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract all biomarkers from this lab report:\n\n{combined_data[:8000]}"}
        ])
        
        # Process the agent's output
        biomarkers = []
        for bio in result.biomarkers:
            std_name = standardize_biomarker_name(bio.name)
            category = get_biomarker_category(std_name)
            flag = get_flag(std_name, bio.value)
            
            biomarkers.append({
                "name": bio.name,
                "standardized_name": std_name,
                "category": category,
                "value": bio.value,
                "unit": bio.unit,
                "reference_min": bio.reference_min,
                "reference_max": bio.reference_max,
                "flag": flag,
                "is_abnormal": flag is not None,
            })
        
        logger.info(f"Agent extracted {len(biomarkers)} biomarkers")
        
        return {
            "biomarkers": biomarkers,
            "report_type": result.report_type,
            "lab_name": result.lab_name,
        }
        
    except Exception as e:
        logger.error(f"Agent extraction failed: {e}")
        return {
            "errors": [f"Agent extraction failed: {str(e)}"],
            "biomarkers": [],
            "report_type": "OTHER",
        }


# ============ NODE 9: SAVE RESULTS ============

async def save_results(state: LabExtractionState) -> dict:
    """
    Save extracted data to MongoDB.
    """
    logger.info("Saving results to database")
    
    try:
        # Create lab report document
        report_date = datetime.fromisoformat(state["report_date"]) if state.get("report_date") else datetime.utcnow()
        
        lab_report = LabReport(
            patient_id=state["patient_id"],
            clinic_id=state["clinic_id"],
            report_date=report_date,
            lab_name=state.get("lab_name"),
            report_type=state.get("report_type", "OTHER"),
            pdf_url=state["pdf_path"],  # In production, this would be a cloud storage URL
            status=ReportStatus.COMPLETED.value,
            thread_id=state["thread_id"],
            raw_text=state.get("extracted_text", "")[:10000],  # Limit raw text
            processed_at=datetime.utcnow(),
        )
        
        await lab_report.insert()
        report_id = str(lab_report.id)
        
        logger.info(f"Created lab report: {report_id}")
        
        # Create biomarker documents
        biomarker_count = 0
        for bio in state.get("biomarkers", []):
            biomarker = Biomarker(
                patient_id=state["patient_id"],
                report_id=report_id,
                clinic_id=state["clinic_id"],
                name=bio["name"],
                standardized_name=bio["standardized_name"],
                category=bio["category"],
                value=bio["value"],
                unit=bio["unit"],
                reference_min=bio.get("reference_min"),
                reference_max=bio.get("reference_max"),
                flag=bio.get("flag"),
                is_abnormal=bio.get("is_abnormal", False),
                test_date=report_date,
            )
            await biomarker.insert()
            biomarker_count += 1
            
            # Update trend document
            trend = await BiomarkerTrend.find_one({
                "patient_id": state["patient_id"],
                "biomarker_name": bio["standardized_name"]
            })
            
            reading = BiomarkerReading(
                date=report_date,
                value=bio["value"],
                unit=bio["unit"],
                flag=bio.get("flag"),
                report_id=report_id,
            )
            
            if trend:
                trend.add_reading(reading)
                await trend.save()
            else:
                # Create new trend document
                trend = BiomarkerTrend(
                    patient_id=state["patient_id"],
                    biomarker_name=bio["standardized_name"],
                    category=bio["category"],
                    readings=[reading],
                    latest_value=bio["value"],
                    latest_unit=bio["unit"],
                    latest_date=report_date,
                    latest_flag=bio.get("flag"),
                    min_value=bio["value"],
                    max_value=bio["value"],
                    average_value=bio["value"],
                    reading_count=1,
                )
                await trend.insert()
        
        logger.info(f"Saved {biomarker_count} biomarkers")
        
        return {
            "report_id": report_id,
            "status": "completed",
        }
        
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
        return {
            "errors": [f"Failed to save results: {str(e)}"],
            "status": "failed",
        }


# ============ ROUTING FUNCTIONS ============

def route_after_encryption_check(state: LabExtractionState) -> Literal["request_password", "extract_text"]:
    """Route based on encryption status."""
    if state.get("is_encrypted"):
        return "request_password"
    return "extract_text"


def route_after_decrypt(state: LabExtractionState) -> Literal["request_password", "extract_text"]:
    """Route based on decryption result."""
    if state.get("decrypt_error"):
        return "request_password"  # Ask for password again
    return "extract_text"


def route_after_extract(state: LabExtractionState) -> Literal["vision_extraction", "collect_data"]:
    """Route based on whether vision is needed."""
    if state.get("needs_vision"):
        return "vision_extraction"
    return "collect_data"

