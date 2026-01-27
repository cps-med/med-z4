# -----------------------------------------------------------
# app/routes/dashboard.py
# -----------------------------------------------------------

from fastapi import APIRouter, Request, Cookie, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Optional

from database import get_db
from app.services.auth_service import validate_session
from app.services.ccow_service import ccow_service
from config import settings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_id: Optional[str] = Cookie(None, alias=settings.session.cookie_name)
):
    """Display patient roster with session validation."""

    # Validate session against database
    user_info = await validate_session(db, session_id) if session_id else None

    if not user_info:
        return RedirectResponse(url="/login", status_code=303)

    # Get current CCOW context (may have been set by med-z1)
    # CCOW Vault validates session and returns context for this user
    current_patient_icn = None
    ccow_context = await ccow_service.get_active_patient(session_id)

    if ccow_context:
        current_patient_icn = ccow_context.get("patient_id")

    # Query patients from database
    result = await db.execute(
        text("""
            SELECT
                patient_key,
                icn,
                name_display,
                dob,
                ssn_last4
            FROM clinical.patient_demographics
            ORDER BY name_last, name_first
            LIMIT 50
        """)
    )

    patients = [
        {
            "patient_key": row[0],
            "icn": row[1],
            "name_display": row[2],
            "dob": row[3].strftime("%Y-%m-%d") if row[3] else "N/A",
            "ssn_last4": row[4] or "N/A",
            "is_selected": row[1] == current_patient_icn  # Highlight current context patient
        }
        for row in result.fetchall()
    ]

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "settings": settings,
            "patients": patients,
            "user": user_info,
            "current_patient_icn": current_patient_icn,
            "ccow_active": ccow_context is not None,
        }
    )


@router.get("/context/banner")
async def get_context_banner(
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_id: Optional[str] = Cookie(None, alias=settings.session.cookie_name)
):
    """
    HTMX endpoint to get current CCOW context banner.
    Polled every 5 seconds to detect context changes from other apps.
    Returns the ccow_banner.html partial.
    """
    context = None

    if session_id:
        # Get current context from CCOW Vault
        ccow_response = await ccow_service.get_active_patient(session_id)

        if ccow_response and ccow_response.get("patient_id"):
            patient_icn = ccow_response.get("patient_id")

            # Look up patient name for display
            result = await db.execute(
                text("""
                    SELECT name_display
                    FROM clinical.patient_demographics
                    WHERE icn = :icn
                    LIMIT 1
                """),
                {"icn": patient_icn}
            )
            patient_row = result.fetchone()

            context = {
                "patient_id": patient_icn,
                "patient_name": patient_row[0] if patient_row else None,
                "set_by": ccow_response.get("set_by", "unknown")
            }

    return templates.TemplateResponse(
        "partials/ccow_banner.html",
        {
            "request": request,
            "context": context
        }
    )


@router.delete("/context/clear")
async def clear_context(
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_id: Optional[str] = Cookie(None, alias=settings.session.cookie_name)
):
    """
    Clear the current CCOW patient context.
    Called when user clicks "Clear" button in the CCOW banner.
    Returns JSON response; HTMX will trigger banner refresh.
    """
    if not session_id:
        return {"success": False, "error": "No session"}

    # Validate session
    user_info = await validate_session(db, session_id) if session_id else None
    if not user_info:
        return {"success": False, "error": "Invalid session"}

    # Clear context in CCOW Vault
    success = await ccow_service.clear_active_patient(session_id)

    if success:
        return {"success": True, "message": "Context cleared"}
    else:
        return {"success": False, "error": "Failed to clear context"}