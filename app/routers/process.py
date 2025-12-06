"""Lab report processing endpoints."""

import os
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.config import settings
from app.core.logging import logger
from app.schemas.extraction import (
    ProcessResponse,
    ResumeRequest,
    ResumeDateRequest,
    LabReportListResponse,
    BiomarkerHistoryResponse,
)
from app.models.lab_report import LabReport, ReportStatus
from app.models.biomarker import Biomarker, BiomarkerTrend
from app.graphs.lab_extraction import lab_extraction_graph
from app.services.vision_service import VisionService
from app.data.biomarker_mapping import standardize_biomarker_name, get_biomarker_category, get_flag, get_reference_range

router = APIRouter(prefix="/process", tags=["Lab Processing"])


# Store for tracking ongoing workflows
workflow_store: dict = {}

# Supported file extensions
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
SUPPORTED_PDF_EXTENSIONS = {".pdf"}
ALL_SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_PDF_EXTENSIONS


class ProcessLabReportRequest(BaseModel):
    """Request body for processing a lab report."""
    patient_id: str
    clinic_id: str
    report_date: Optional[str] = None
    pdf_password: Optional[str] = None


def get_file_extension(filename: str) -> str:
    """Get lowercase file extension."""
    return Path(filename).suffix.lower()


def is_image_file(filename: str) -> bool:
    """Check if file is an image."""
    return get_file_extension(filename) in SUPPORTED_IMAGE_EXTENSIONS


def is_pdf_file(filename: str) -> bool:
    """Check if file is a PDF."""
    return get_file_extension(filename) in SUPPORTED_PDF_EXTENSIONS


@router.post("/lab-report", response_model=ProcessResponse)
async def process_lab_report(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    clinic_id: str = Form(...),
    report_date: str = Form(None),
    pdf_password: str = Form(None),
):
    """
    Upload and process a lab report (PDF or image).
    
    Supported formats: PDF, PNG, JPG, JPEG, WEBP, GIF
    
    The workflow will:
    1. For PDFs: Check if encrypted, extract text/tables, use Vision if needed
    2. For Images: Use Vision API directly
    3. Standardize biomarkers
    4. Save to database
    
    If date cannot be extracted and wasn't provided, returns status="waiting_date".
    
    Returns thread_id for tracking/resuming the workflow.
    """
    # Validate file type
    file_ext = get_file_extension(file.filename)
    if file_ext not in ALL_SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Accepted formats: PDF, PNG, JPG, JPEG, WEBP, GIF"
        )
    
    logger.info(f"Receiving upload for patient {patient_id}, file: {file.filename}")
    
    # Generate unique thread_id
    thread_id = str(uuid.uuid4())
    
    # Create upload directory
    upload_dir = Path(settings.UPLOAD_DIR) / thread_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Save the uploaded file
    file_path = str(upload_dir / file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    # Check if it's an image - process differently
    if is_image_file(file.filename):
        return await process_image_report(
            file_path=file_path,
            patient_id=patient_id,
            clinic_id=clinic_id,
            thread_id=thread_id,
            report_date=report_date,
        )
    
    # PDF processing - use the graph workflow
    initial_state = {
        "pdf_path": file_path,
        "patient_id": patient_id,
        "clinic_id": clinic_id,
        "thread_id": thread_id,
        "report_date": report_date,  # Don't default to now - let AI extract
        "user_provided_date": report_date is not None,
        "is_encrypted": False,
        "password": pdf_password,
        "decrypt_error": None,
        "extracted_text": "",
        "extracted_tables": [],
        "needs_vision": False,
        "image_paths": [],
        "vision_data": {},
        "combined_data": "",
        "report_type": "OTHER",
        "lab_name": None,
        "biomarkers": [],
        "report_id": None,
        "status": "processing",
        "errors": [],
    }
    
    # Run the workflow
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        result = await lab_extraction_graph.ainvoke(initial_state, config)
        
        # Store the result for retrieval
        workflow_store[thread_id] = result
        
        # Check if workflow is waiting for password
        if result.get("status") == "waiting_password":
            return ProcessResponse(
                status="waiting_password",
                thread_id=thread_id,
                message="PDF is encrypted. Please provide the password.",
                result=None,
            )
        
        # Check if waiting for date
        if result.get("status") == "waiting_date":
            return ProcessResponse(
                status="waiting_date",
                thread_id=thread_id,
                message="Could not extract report date. Please provide the test date.",
                result=None,
            )
        
        # Check for errors
        if result.get("errors"):
            return ProcessResponse(
                status="failed",
                thread_id=thread_id,
                message="; ".join(result["errors"]),
                result=None,
            )
        
        # Success
        return ProcessResponse(
            status="completed",
            thread_id=thread_id,
            report_id=result.get("report_id"),
            message=f"Successfully processed {len(result.get('biomarkers', []))} biomarkers",
            result={
                "report_type": result.get("report_type"),
                "lab_name": result.get("lab_name"),
                "biomarkers": result.get("biomarkers", []),
                "total_biomarkers": len(result.get("biomarkers", [])),
                "abnormal_count": sum(1 for b in result.get("biomarkers", []) if b.get("is_abnormal")),
            },
        )
        
    except Exception as e:
        # Handle interrupt (password required)
        if "interrupt" in str(type(e)).lower():
            workflow_store[thread_id] = {"status": "waiting_password", "pdf_path": file_path}
            return ProcessResponse(
                status="waiting_password",
                thread_id=thread_id,
                message="PDF is encrypted. Please provide the password.",
                result=None,
            )
        
        logger.error(f"Error processing lab report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_image_report(
    file_path: str,
    patient_id: str,
    clinic_id: str,
    thread_id: str,
    report_date: Optional[str] = None,
) -> ProcessResponse:
    """
    Process an image file directly using Vision API.
    """
    logger.info(f"Processing image report: {file_path}")
    
    try:
        vision_service = VisionService()
        vision_result = vision_service.extract_from_image(file_path)
        
        if "error" in vision_result:
            logger.error(f"Vision extraction failed: {vision_result['error']}")
            return ProcessResponse(
                status="failed",
                thread_id=thread_id,
                message=f"Failed to extract data from image: {vision_result['error']}",
                result=None,
            )
        
        # Extract date from vision result or use provided
        extracted_date = vision_result.get("report_date")
        final_date = report_date or extracted_date
        
        # If no date, ask user
        if not final_date:
            workflow_store[thread_id] = {
                "status": "waiting_date",
                "file_path": file_path,
                "patient_id": patient_id,
                "clinic_id": clinic_id,
                "vision_result": vision_result,
            }
            return ProcessResponse(
                status="waiting_date",
                thread_id=thread_id,
                message="Could not extract report date from image. Please provide the test date.",
                result=None,
            )
        
        # Parse and standardize biomarkers
        biomarkers = []
        for item in vision_result.get("biomarkers", []):
            name = item.get("name")
            value = item.get("value")
            unit = item.get("unit", "")
            
            if not name or value is None:
                continue
            
            try:
                value = float(value)
            except (ValueError, TypeError):
                continue
            
            standardized_name = standardize_biomarker_name(name)
            category = get_biomarker_category(standardized_name)
            ref_min, ref_max = get_reference_range(
                standardized_name, 
                f"{item.get('reference_min', '')}-{item.get('reference_max', '')}" if item.get('reference_min') else None
            )
            
            # Use reference from vision if available
            if item.get("reference_min") is not None:
                ref_min = float(item["reference_min"])
            if item.get("reference_max") is not None:
                ref_max = float(item["reference_max"])
            
            flag = get_flag(standardized_name, value, ref_min, ref_max)
            is_abnormal = flag is not None
            
            biomarkers.append({
                "name": name,
                "standardized_name": standardized_name,
                "category": category,
                "value": value,
                "unit": unit,
                "reference_min": ref_min,
                "reference_max": ref_max,
                "flag": flag,
                "is_abnormal": is_abnormal,
            })
        
        logger.info(f"Extracted {len(biomarkers)} biomarkers from image")
        
        # Save to database
        report_datetime = datetime.fromisoformat(final_date.replace("Z", "+00:00")) if "T" in final_date else datetime.strptime(final_date, "%Y-%m-%d")
        
        lab_report = LabReport(
            patient_id=patient_id,
            clinic_id=clinic_id,
            report_date=report_datetime,
            lab_name=vision_result.get("lab_name"),
            report_type=vision_result.get("report_type", "OTHER"),
            status="completed",
            thread_id=thread_id,
        )
        await lab_report.insert()
        
        report_id = str(lab_report.id)
        logger.info(f"Created lab report: {report_id}")
        
        # Save biomarkers
        for bm in biomarkers:
            biomarker = Biomarker(
                patient_id=patient_id,
                report_id=report_id,
                clinic_id=clinic_id,
                name=bm["name"],
                standardized_name=bm["standardized_name"],
                category=bm["category"],
                value=bm["value"],
                unit=bm["unit"],
                reference_min=bm.get("reference_min"),
                reference_max=bm.get("reference_max"),
                flag=bm.get("flag"),
                is_abnormal=bm.get("is_abnormal", False),
                test_date=report_datetime,
            )
            await biomarker.insert()
            
            # Update or create trend
            await update_biomarker_trend(biomarker)
        
        logger.info(f"Saved {len(biomarkers)} biomarkers")
        
        return ProcessResponse(
            status="completed",
            thread_id=thread_id,
            report_id=report_id,
            message=f"Successfully processed {len(biomarkers)} biomarkers",
            result={
                "report_type": vision_result.get("report_type", "OTHER"),
                "lab_name": vision_result.get("lab_name"),
                "biomarkers": biomarkers,
                "total_biomarkers": len(biomarkers),
                "abnormal_count": sum(1 for b in biomarkers if b.get("is_abnormal")),
            },
        )
        
    except Exception as e:
        logger.error(f"Error processing image report: {e}")
        return ProcessResponse(
            status="failed",
            thread_id=thread_id,
            message=str(e),
            result=None,
        )


async def update_biomarker_trend(biomarker: Biomarker):
    """Update or create a biomarker trend record."""
    from app.models.biomarker import BiomarkerReading
    
    trend = await BiomarkerTrend.find_one({
        "patient_id": biomarker.patient_id,
        "biomarker_name": biomarker.standardized_name,
    })
    
    new_reading = BiomarkerReading(
        date=biomarker.test_date,
        value=biomarker.value,
        unit=biomarker.unit,
        flag=biomarker.flag,
        report_id=biomarker.report_id,
    )
    
    if trend:
        # Add reading and update stats
        trend.readings.append(new_reading)
        trend.readings.sort(key=lambda r: r.date)
        
        values = [r.value for r in trend.readings]
        trend.latest_value = biomarker.value
        trend.latest_unit = biomarker.unit
        trend.latest_date = biomarker.test_date
        trend.latest_flag = biomarker.flag
        trend.reading_count = len(trend.readings)
        trend.min_value = min(values)
        trend.max_value = max(values)
        trend.average_value = sum(values) / len(values)
        
        # Calculate trend
        if len(values) >= 2:
            change = values[-1] - values[-2]
            trend.trend_percent = (change / values[-2]) * 100 if values[-2] != 0 else 0
            trend.trend_direction = "increasing" if change > 0 else "decreasing" if change < 0 else "stable"
        
        await trend.save()
    else:
        # Create new trend
        trend = BiomarkerTrend(
            patient_id=biomarker.patient_id,
            clinic_id=biomarker.clinic_id,
            biomarker_name=biomarker.standardized_name,
            category=biomarker.category,
            readings=[new_reading],
            latest_value=biomarker.value,
            latest_unit=biomarker.unit,
            latest_date=biomarker.test_date,
            latest_flag=biomarker.flag,
            reading_count=1,
            min_value=biomarker.value,
            max_value=biomarker.value,
            average_value=biomarker.value,
            trend_direction="stable",
            trend_percent=0,
        )
        await trend.insert()


@router.post("/resume/{thread_id}", response_model=ProcessResponse)
async def resume_with_password(thread_id: str, request: ResumeRequest):
    """
    Resume a paused workflow by providing the PDF password.
    """
    if thread_id not in workflow_store:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        # Resume with the password
        result = await lab_extraction_graph.ainvoke(
            {"password": request.password},
            config,
        )
        
        workflow_store[thread_id] = result
        
        # Check for decrypt error
        if result.get("decrypt_error"):
            return ProcessResponse(
                status="waiting_password",
                thread_id=thread_id,
                message=f"Decryption failed: {result['decrypt_error']}. Please try again.",
                result=None,
            )
        
        # Check for other errors
        if result.get("errors"):
            return ProcessResponse(
                status="failed",
                thread_id=thread_id,
                message="; ".join(result["errors"]),
                result=None,
            )
        
        # Success
        return ProcessResponse(
            status="completed",
            thread_id=thread_id,
            report_id=result.get("report_id"),
            message=f"Successfully processed {len(result.get('biomarkers', []))} biomarkers",
            result={
                "report_type": result.get("report_type"),
                "lab_name": result.get("lab_name"),
                "biomarkers": result.get("biomarkers", []),
                "total_biomarkers": len(result.get("biomarkers", [])),
                "abnormal_count": sum(1 for b in result.get("biomarkers", []) if b.get("is_abnormal")),
            },
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume-date/{thread_id}", response_model=ProcessResponse)
async def resume_with_date(thread_id: str, request: ResumeDateRequest):
    """
    Resume a paused workflow by providing the report date.
    """
    if thread_id not in workflow_store:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    stored = workflow_store[thread_id]
    
    if stored.get("status") != "waiting_date":
        raise HTTPException(status_code=400, detail="Workflow is not waiting for date")
    
    # For image files, we have vision_result stored
    if "vision_result" in stored:
        return await process_image_report(
            file_path=stored["file_path"],
            patient_id=stored["patient_id"],
            clinic_id=stored["clinic_id"],
            thread_id=thread_id,
            report_date=request.report_date,
        )
    
    # For PDFs, resume the graph workflow
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        result = await lab_extraction_graph.ainvoke(
            {"report_date": request.report_date, "user_provided_date": True},
            config,
        )
        
        workflow_store[thread_id] = result
        
        if result.get("errors"):
            return ProcessResponse(
                status="failed",
                thread_id=thread_id,
                message="; ".join(result["errors"]),
                result=None,
            )
        
        return ProcessResponse(
            status="completed",
            thread_id=thread_id,
            report_id=result.get("report_id"),
            message=f"Successfully processed {len(result.get('biomarkers', []))} biomarkers",
            result={
                "report_type": result.get("report_type"),
                "lab_name": result.get("lab_name"),
                "biomarkers": result.get("biomarkers", []),
                "total_biomarkers": len(result.get("biomarkers", [])),
                "abnormal_count": sum(1 for b in result.get("biomarkers", []) if b.get("is_abnormal")),
            },
        )
        
    except Exception as e:
        logger.error(f"Error resuming with date: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{thread_id}")
async def get_workflow_status(thread_id: str):
    """Get the status of a processing workflow."""
    if thread_id not in workflow_store:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    result = workflow_store[thread_id]
    return {
        "thread_id": thread_id,
        "status": result.get("status", "unknown"),
        "errors": result.get("errors", []),
    }


# ============ QUERY ENDPOINTS ============

reports_router = APIRouter(prefix="/reports", tags=["Lab Reports"])


@reports_router.get("/{patient_id}", response_model=LabReportListResponse)
async def get_patient_reports(patient_id: str, limit: int = 50, skip: int = 0):
    """Get all lab reports for a patient."""
    reports = await LabReport.find(
        LabReport.patient_id == patient_id
    ).sort(-LabReport.report_date).skip(skip).limit(limit).to_list()
    
    total = await LabReport.find(LabReport.patient_id == patient_id).count()
    
    return LabReportListResponse(
        reports=[
            {
                "id": str(r.id),
                "patient_id": r.patient_id,
                "clinic_id": r.clinic_id,
                "report_date": r.report_date.isoformat(),
                "report_type": r.report_type,
                "lab_name": r.lab_name,
                "status": r.status,
            }
            for r in reports
        ],
        total=total,
    )


@reports_router.get("/{patient_id}/{report_id}")
async def get_report_details(patient_id: str, report_id: str):
    """Get detailed report with all biomarkers."""
    report = await LabReport.get(report_id)
    
    if not report or report.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Report not found")
    
    biomarkers = await Biomarker.find(
        Biomarker.report_id == report_id
    ).to_list()
    
    return {
        "report": {
            "id": str(report.id),
            "patient_id": report.patient_id,
            "report_date": report.report_date.isoformat(),
            "report_type": report.report_type,
            "lab_name": report.lab_name,
            "status": report.status,
        },
        "biomarkers": [
            {
                "id": str(b.id),
                "name": b.name,
                "standardized_name": b.standardized_name,
                "category": b.category,
                "value": b.value,
                "unit": b.unit,
                "reference_min": b.reference_min,
                "reference_max": b.reference_max,
                "flag": b.flag,
                "is_abnormal": b.is_abnormal,
            }
            for b in biomarkers
        ],
    }


# ============ BIOMARKER ENDPOINTS ============

biomarkers_router = APIRouter(prefix="/biomarkers", tags=["Biomarkers"])


@biomarkers_router.get("/{patient_id}")
async def get_patient_biomarkers(patient_id: str, category: Optional[str] = None):
    """Get all unique biomarker trends for a patient."""
    query = {"patient_id": patient_id}
    if category:
        query["category"] = category
    
    trends = await BiomarkerTrend.find(query).to_list()
    
    return {
        "patient_id": patient_id,
        "trends": [
            {
                "biomarker_name": t.biomarker_name,
                "category": t.category,
                "latest_value": t.latest_value,
                "latest_unit": t.latest_unit,
                "latest_date": t.latest_date.isoformat(),
                "latest_flag": t.latest_flag,
                "trend_direction": t.trend_direction,
                "trend_percent": t.trend_percent,
                "reading_count": t.reading_count,
                "min_value": t.min_value,
                "max_value": t.max_value,
                "average_value": t.average_value,
            }
            for t in trends
        ],
    }


@biomarkers_router.get("/{patient_id}/{biomarker_name}/history")
async def get_biomarker_history(patient_id: str, biomarker_name: str):
    """Get full history for a specific biomarker."""
    trend = await BiomarkerTrend.find_one({
        "patient_id": patient_id,
        "biomarker_name": biomarker_name.lower(),
    })
    
    if not trend:
        raise HTTPException(status_code=404, detail="Biomarker not found")
    
    return BiomarkerHistoryResponse(
        patient_id=patient_id,
        biomarker_name=trend.biomarker_name,
        category=trend.category,
        readings=[
            {
                "date": r.date.isoformat(),
                "value": r.value,
                "unit": r.unit,
                "flag": r.flag,
                "report_id": r.report_id,
            }
            for r in trend.readings
        ],
        trend_direction=trend.trend_direction,
        trend_percent=trend.trend_percent,
        latest_value=trend.latest_value,
        latest_unit=trend.latest_unit,
        latest_flag=trend.latest_flag,
    )

