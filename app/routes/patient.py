# -----------------------------------------------------------
# app/routes/patient.py
# -----------------------------------------------------------

from fastapi import APIRouter, Request, Cookie, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from database import get_db
from app.services.auth_service import validate_session
from app.services.ccow_service import ccow_service
from app.services.patient_service import (
    get_patient_demographics,
    get_patient_vitals,
    get_patient_allergies,
    get_patient_medications
)
from config import settings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)


@router.get("/patient/{icn}", response_class=HTMLResponse)
async def patient_detail(
    icn: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_id: Optional[str] = Cookie(None, alias=settings.session.cookie_name)
):
    """
    Display patient detail page with clinical data.
    Automatically sets CCOW context to this patient.
    """

    # Validate session
    user_info = await validate_session(db, session_id) if session_id else None

    if not user_info:
        return RedirectResponse(url="/login", status_code=303)

    # Fetch patient demographics
    patient = await get_patient_demographics(db, icn)

    if not patient:
        # Patient not found - redirect to dashboard
        logger.warning(f"Patient not found: {icn}")
        return RedirectResponse(url="/dashboard", status_code=303)

    # Automatically set CCOW context to this patient
    await ccow_service.set_active_patient(session_id, icn)

    # Fetch clinical data
    vitals = await get_patient_vitals(db, patient["patient_key"])
    allergies = await get_patient_allergies(db, patient["patient_key"])
    medications = await get_patient_medications(db, patient["patient_key"])

    return templates.TemplateResponse(
        "patient_detail.html",
        {
            "request": request,
            "settings": settings,
            "user": user_info,
            "patient": patient,
            "vitals": vitals,
            "allergies": allergies,
            "medications": medications,
        }
    )