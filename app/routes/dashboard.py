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

    # Query real patients from database
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
        }
        for row in result.fetchall()
    ]

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "settings": settings,
            "patients": patients,
            "user": user_info,  # Pass user info to template (optional)
        }
    )