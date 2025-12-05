"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "ai-health-passport",
        "version": "0.1.0"
    }


@router.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes/Docker."""
    return {"status": "ready"}

