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
templates.env.auto_reload = True  # Enable auto-reload for development


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
                age,
                sex,
                ssn_last4,
                primary_station
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
            "dob": row[3].strftime("%Y-%m-%d") if row[3] else "—",
            "age": row[4] if row[4] is not None else "—",
            "sex": row[5] or "—",
            "ssn_last4": row[6] or "—",
            "primary_station": row[7] or "—",
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


@router.get("/ccow/poll", response_class=HTMLResponse)
async def ccow_poll(
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_id: Optional[str] = Cookie(None, alias=settings.session.cookie_name),
    current_icn: Optional[str] = None
):
    """
    HTMX endpoint to poll CCOW context.
    Returns HTML fragment with notification if context changed.
    Detects when another app (e.g., med-z1) changes the patient context.
    """
    if not session_id:
        return ""

    # Get current CCOW context
    ccow_context = await ccow_service.get_active_patient(session_id)

    if not ccow_context:
        # No context set - if UI shows a patient, that's stale
        if current_icn:
            return """
            <div id="context-notification" hx-get="/ccow/poll?current_icn={}" hx-trigger="every 5s" hx-swap="outerHTML">
                <div class="notification warning">
                    Patient context has been cleared.
                    <button class="btn-sm" onclick="window.location.reload()">
                        Refresh
                    </button>
                </div>
            </div>
            """.format(current_icn)
        return '<div id="context-notification" hx-get="/ccow/poll" hx-trigger="every 5s" hx-swap="outerHTML"></div>'

    ccow_patient_icn = ccow_context.get("patient_id")

    # If context changed from what UI is showing
    if ccow_patient_icn and ccow_patient_icn != current_icn:
        # Get patient details for notification
        result = await db.execute(
            text("""
                SELECT name_display
                FROM clinical.patient_demographics
                WHERE icn = :icn
                LIMIT 1
            """),
            {"icn": ccow_patient_icn}
        )
        patient_row = result.fetchone()
        patient_name = patient_row[0] if patient_row else "Unknown Patient"

        # Return HTMX fragment to show notification
        # IMPORTANT: Keep passing the OLD current_icn so notification stays visible
        # until user clicks Refresh. If we passed the NEW icn, the next poll would
        # see "no change" and hide the notification after 5 seconds.
        current_icn_param = f"?current_icn={current_icn}" if current_icn else ""
        return f"""
        <div id="context-notification" hx-get="/ccow/poll{current_icn_param}" hx-trigger="every 5s" hx-swap="outerHTML">
            <div class="notification info">
                Context changed to: <strong>{patient_name}</strong> (ICN: {ccow_patient_icn})
                <button class="btn-sm" onclick="window.location.reload()">
                    Refresh
                </button>
            </div>
        </div>
        """

    # No change - return empty div but keep HTMX attributes for continued polling
    if current_icn:
        return f'<div id="context-notification" hx-get="/ccow/poll?current_icn={current_icn}" hx-trigger="every 5s" hx-swap="outerHTML"></div>'
    else:
        return '<div id="context-notification" hx-get="/ccow/poll" hx-trigger="every 5s" hx-swap="outerHTML"></div>'


@router.post("/patient/select/{icn}")
async def select_patient(
    icn: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_id: Optional[str] = Cookie(None, alias=settings.session.cookie_name)
):
    """
    Set CCOW context to the selected patient.
    Called when user clicks "View" button on a patient.
    """
    if not session_id:
        return {"success": False, "error": "No session"}

    # Validate session
    user_info = await validate_session(db, session_id)
    if not user_info:
        return {"success": False, "error": "Invalid session"}

    # Set CCOW context via X-Session-ID header
    success = await ccow_service.set_active_patient(session_id, icn)

    if success:
        # Get patient name for response
        result = await db.execute(
            text("""
                SELECT name_display
                FROM clinical.patient_demographics
                WHERE icn = :icn
                LIMIT 1
            """),
            {"icn": icn}
        )
        patient_row = result.fetchone()
        patient_name = patient_row[0] if patient_row else "Unknown Patient"

        return {
            "success": True,
            "patient_name": patient_name,
            "patient_icn": icn
        }
    else:
        return {"success": False, "error": "Failed to set CCOW context"}