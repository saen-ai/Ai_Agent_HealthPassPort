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
from app.schemas.extraction import (
    ProcessResponse,
    ResumeRequest,
    LabReportListResponse,
    BiomarkerHistoryResponse,
)
from app.models.lab_report import LabReport, ReportStatus
from app.models.biomarker import Biomarker, BiomarkerTrend
from app.graphs.lab_extraction import lab_extraction_graph

router = APIRouter(prefix="/process", tags=["Lab Processing"])


# Store for tracking ongoing workflows
workflow_store: dict = {}


class ProcessLabReportRequest(BaseModel):
    """Request body for processing a lab report."""
    patient_id: str
    clinic_id: str
    report_date: Optional[str] = None
    pdf_password: Optional[str] = None


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
    Upload and process a lab report PDF.
    
    The workflow will:
    1. Check if PDF is encrypted
    2. If encrypted, return status="waiting_password" and pause
    3. Extract text and tables
    4. Use Vision API if needed
    5. Standardize biomarkers
    6. Save to database
    
    Returns thread_id for tracking/resuming the workflow.
    """
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    # Generate unique thread_id
    thread_id = str(uuid.uuid4())
    
    # Create upload directory
    upload_dir = Path(settings.UPLOAD_DIR) / thread_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Save the uploaded file
    pdf_path = str(upload_dir / file.filename)
    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    # Prepare initial state
    initial_state = {
        "pdf_path": pdf_path,
        "patient_id": patient_id,
        "clinic_id": clinic_id,
        "thread_id": thread_id,
        "report_date": report_date or datetime.utcnow().isoformat(),
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
            workflow_store[thread_id] = {"status": "waiting_password", "pdf_path": pdf_path}
            return ProcessResponse(
                status="waiting_password",
                thread_id=thread_id,
                message="PDF is encrypted. Please provide the password.",
                result=None,
            )
        
        raise HTTPException(status_code=500, detail=str(e))


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

