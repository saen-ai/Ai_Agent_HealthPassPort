# Patient Management Feature

from app.features.patients.models import Patient
from app.features.patients.router import router
from app.features.patients.service import PatientService

__all__ = ["Patient", "router", "PatientService"]

