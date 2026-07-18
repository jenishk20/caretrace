"""Shared FastAPI helpers used across feature routers."""
from __future__ import annotations

from fastapi import HTTPException

from core import db


def require_staff(staff_id: int) -> dict:
    staff = db.get_staff(staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail=f"Staff {staff_id} not found")
    return staff


def require_patient(patient_id: int) -> dict:
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    return patient
