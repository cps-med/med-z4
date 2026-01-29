# -----------------------------------------------------------
# app/routes/monitoring.py
# -----------------------------------------------------------
# System monitoring and health check route handlers
# -----------------------------------------------------------

from fastapi import APIRouter, Request, Cookie, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database import get_db
from app.services.auth_service import validate_session
from app.services import monitoring_service
from config import settings

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/sessions", response_class=HTMLResponse)
async def get_sessions_monitor(
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_id: Optional[str] = Cookie(None, alias=settings.session.cookie_name)
):
    """
    Display active sessions table.
    Requires valid session authentication.
    """
    # Validate session
    user_info = await validate_session(db, session_id) if session_id else None
    if not user_info:
        return """
        <div class="error-msg">
            <strong>Error:</strong> Authentication required
        </div>
        """

    # Fetch sessions data
    data = await monitoring_service.get_active_sessions(db)

    if not data.get("success"):
        return f"""
        <div class="error-msg">
            <strong>Error:</strong> {data.get('error', 'Failed to fetch sessions')}
        </div>
        """

    return templates.TemplateResponse(
        "partials/monitoring_sessions.html",
        {
            "request": request,
            "summary": data.get("summary"),
            "sessions": data.get("sessions", [])
        }
    )


@router.get("/database", response_class=HTMLResponse)
async def get_database_monitor(
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_id: Optional[str] = Cookie(None, alias=settings.session.cookie_name)
):
    """
    Display database health check results.
    """
    # Validate session
    user_info = await validate_session(db, session_id) if session_id else None
    if not user_info:
        return """
        <div class="error-msg">
            <strong>Error:</strong> Authentication required
        </div>
        """

    # Fetch database health
    data = await monitoring_service.get_database_health(db)

    color = "green" if data.get("success") else "red"

    if data.get("success"):
        return f"""
        <div class="success-msg" style="border-color: {color};">
            <strong>Database Status:</strong> {data.get('status')}<br>
            <strong>Patients:</strong> {data.get('patient_count'):,}<br>
            <strong>Last ETL:</strong> {data.get('last_etl_update')}<br>
            <strong>Response Time:</strong> {data.get('response_time_ms')}ms
        </div>
        """
    else:
        return f"""
        <div class="error-msg" style="border-color: {color};">
            <strong>Database Status:</strong> {data.get('status')}<br>
            <strong>Error:</strong> {data.get('error', 'Unknown error')}
        </div>
        """


@router.get("/medz1", response_class=HTMLResponse)
async def get_medz1_monitor(
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_id: Optional[str] = Cookie(None, alias=settings.session.cookie_name)
):
    """
    Display med-z1 health check results.
    """
    # Validate session
    user_info = await validate_session(db, session_id) if session_id else None
    if not user_info:
        return """
        <div class="error-msg">
            <strong>Error:</strong> Authentication required
        </div>
        """

    # Fetch med-z1 health
    data = await monitoring_service.get_medz1_health()

    color = "green" if data.get("success") else "red"

    if data.get("success"):
        return f"""
        <div class="success-msg" style="border-color: {color};">
            <strong>med-z1 Status:</strong> {data.get('status')} (Code: {data.get('status_code')})
        </div>
        """
    else:
        return f"""
        <div class="error-msg" style="border-color: {color};">
            <strong>med-z1 Status:</strong> {data.get('status')}<br>
            <strong>Error:</strong> {data.get('error', 'Unknown error')}
        </div>
        """


@router.get("/ccow-patients", response_class=HTMLResponse)
async def get_ccow_patients_monitor(
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_id: Optional[str] = Cookie(None, alias=settings.session.cookie_name)
):
    """
    Display CCOW active patients table.
    """
    # Validate session
    user_info = await validate_session(db, session_id) if session_id else None
    if not user_info or not session_id:
        return """
        <div class="error-msg">
            <strong>Error:</strong> Authentication required
        </div>
        """

    # Fetch CCOW active patients
    data = await monitoring_service.get_ccow_active_patients(session_id)

    if not data.get("success"):
        return f"""
        <div class="error-msg">
            <strong>Error:</strong> {data.get('error', 'Failed to fetch CCOW contexts')}
        </div>
        """

    return templates.TemplateResponse(
        "partials/monitoring_ccow_patients.html",
        {
            "request": request,
            "total_count": data.get("total_count", 0),
            "contexts": data.get("contexts", [])
        }
    )


@router.get("/ccow-history", response_class=HTMLResponse)
async def get_ccow_history_monitor(
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_id: Optional[str] = Cookie(None, alias=settings.session.cookie_name)
):
    """
    Display CCOW context history table.
    """
    # Validate session
    user_info = await validate_session(db, session_id) if session_id else None
    if not user_info or not session_id:
        return """
        <div class="error-msg">
            <strong>Error:</strong> Authentication required
        </div>
        """

    # Fetch CCOW history
    data = await monitoring_service.get_ccow_history(session_id, limit=30)

    if not data.get("success"):
        return f"""
        <div class="error-msg">
            <strong>Error:</strong> {data.get('error', 'Failed to fetch CCOW history')}
        </div>
        """

    return templates.TemplateResponse(
        "partials/monitoring_ccow_history.html",
        {
            "request": request,
            "total_count": data.get("total_count", 0),
            "history": data.get("history", [])
        }
    )
