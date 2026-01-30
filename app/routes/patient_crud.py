# -----------------------------------------------------------
# app/routes/patient_crud.py
# -----------------------------------------------------------
# Patient demographics CRUD route handlers
# -----------------------------------------------------------

from fastapi import APIRouter, Request, Form, Depends, Cookie
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
import logging

from database import get_db
from app.services.auth_service import validate_session
from app.services import patient_crud_service
from app.services.ccow_service import ccow_service
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/patient", tags=["Patient CRUD"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/create-form", response_class=HTMLResponse)
async def get_create_patient_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_id: Optional[str] = Cookie(None, alias=settings.session.cookie_name)
):
    """
    Return modal HTML for creating new patient.
    """
    # Validate session
    user_info = await validate_session(db, session_id) if session_id else None
    if not user_info:
        return """
        <div class="toast toast-error">Authentication required</div>
        """

    return templates.TemplateResponse(
        "partials/patient_create_form.html",
        {
            "request": request,
            "settings": settings
        }
    )


@router.post("/create", response_class=HTMLResponse)
async def create_patient(
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_id: Optional[str] = Cookie(None, alias=settings.session.cookie_name),
    name_last: str = Form(...),
    name_first: str = Form(...),
    dob: str = Form(...),
    sex: str = Form(...),
    ssn: Optional[str] = Form(None),
    primary_station: Optional[str] = Form(None),
    primary_station_name: Optional[str] = Form(None),
    address_street1: Optional[str] = Form(None),
    address_street2: Optional[str] = Form(None),
    address_city: Optional[str] = Form(None),
    address_state: Optional[str] = Form(None),
    address_zip: Optional[str] = Form(None),
    phone_primary: Optional[str] = Form(None),
    insurance_company_name: Optional[str] = Form(None),
    marital_status: Optional[str] = Form(None),
    religion: Optional[str] = Form(None),
    service_connected_percent: Optional[str] = Form(None),
    deceased_flag: Optional[str] = Form(None),
    death_date: Optional[str] = Form(None)
):
    """
    Create new patient. Returns either:
    - Success: Toast + script to close modal and refresh table
    - Error: Form with validation errors
    """
    # Validate session
    user_info = await validate_session(db, session_id) if session_id else None
    if not user_info:
        return """
        <div class="toast toast-error">Authentication required</div>
        """

    # Collect form data
    patient_data = {
        "name_last": name_last,
        "name_first": name_first,
        "dob": dob,
        "sex": sex,
        "ssn": ssn,
        "primary_station": primary_station,
        "primary_station_name": primary_station_name,
        "address_street1": address_street1,
        "address_street2": address_street2,
        "address_city": address_city,
        "address_state": address_state,
        "address_zip": address_zip,
        "phone_primary": phone_primary,
        "insurance_company_name": insurance_company_name,
        "marital_status": marital_status,
        "religion": religion,
        "service_connected_percent": service_connected_percent,
        "deceased_flag": deceased_flag,
        "death_date": death_date
    }

    # Validate
    errors = patient_crud_service.validate_patient_data(patient_data, is_create=True)

    if errors:
        # Return form with errors
        return templates.TemplateResponse(
            "partials/patient_create_form.html",
            {
                "request": request,
                "settings": settings,
                "errors": errors,
                "data": patient_data
            }
        )

    # Create patient
    result = await patient_crud_service.create_patient(db, patient_data)

    if not result["success"]:
        return f"""
        <div class="toast toast-error">Error: {result['error']}</div>
        """

    # Set CCOW context to newly created patient (non-blocking - don't fail if CCOW unavailable)
    try:
        await ccow_service.set_active_patient(
            session_id=session_id,
            patient_icn=result['icn']
        )
    except Exception as e:
        logger.error(f"Failed to set CCOW context after patient creation: {e}")
        # Continue - patient was created successfully even if CCOW failed

    # Success: Return response that closes modal + shows toast + refreshes table
    return f"""
    <div class="toast toast-success">Patient created: {result['name_display']} ({result['icn']})</div>
    <script>
        closeModal();
        document.querySelector('#roster-refresh-trigger').click();
    </script>
    """


@router.get("/{icn}/edit-form", response_class=HTMLResponse)
async def get_edit_patient_form(
    icn: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_id: Optional[str] = Cookie(None, alias=settings.session.cookie_name)
):
    """
    Return modal HTML for editing existing patient.
    """
    # Validate session
    user_info = await validate_session(db, session_id) if session_id else None
    if not user_info:
        return """
        <div class="toast toast-error">Authentication required</div>
        """

    # Fetch patient data
    patient = await patient_crud_service.get_patient_by_icn(db, icn)

    if not patient:
        return f"""
        <div class="toast toast-error">Patient {icn} not found</div>
        """

    return templates.TemplateResponse(
        "partials/patient_edit_form.html",
        {
            "request": request,
            "settings": settings,
            "patient": patient
        }
    )


@router.post("/{icn}/update", response_class=HTMLResponse)
async def update_patient(
    icn: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_id: Optional[str] = Cookie(None, alias=settings.session.cookie_name),
    name_last: str = Form(...),
    name_first: str = Form(...),
    dob: str = Form(...),
    sex: str = Form(...),
    ssn: Optional[str] = Form(None),
    primary_station: Optional[str] = Form(None),
    primary_station_name: Optional[str] = Form(None),
    address_street1: Optional[str] = Form(None),
    address_street2: Optional[str] = Form(None),
    address_city: Optional[str] = Form(None),
    address_state: Optional[str] = Form(None),
    address_zip: Optional[str] = Form(None),
    phone_primary: Optional[str] = Form(None),
    insurance_company_name: Optional[str] = Form(None),
    marital_status: Optional[str] = Form(None),
    religion: Optional[str] = Form(None),
    service_connected_percent: Optional[str] = Form(None),
    deceased_flag: Optional[str] = Form(None),
    death_date: Optional[str] = Form(None)
):
    """
    Update patient. Returns either:
    - Success: Toast + script to close modal and refresh
    - Error: Form with validation errors
    """
    # Validate session
    user_info = await validate_session(db, session_id) if session_id else None
    if not user_info:
        return """
        <div class="toast toast-error">Authentication required</div>
        """

    # Collect form data
    patient_data = {
        "name_last": name_last,
        "name_first": name_first,
        "dob": dob,
        "sex": sex,
        "ssn": ssn,
        "primary_station": primary_station,
        "primary_station_name": primary_station_name,
        "address_street1": address_street1,
        "address_street2": address_street2,
        "address_city": address_city,
        "address_state": address_state,
        "address_zip": address_zip,
        "phone_primary": phone_primary,
        "insurance_company_name": insurance_company_name,
        "marital_status": marital_status,
        "religion": religion,
        "service_connected_percent": service_connected_percent,
        "deceased_flag": deceased_flag,
        "death_date": death_date
    }

    # Validate
    errors = patient_crud_service.validate_patient_data(patient_data, is_create=False)

    if errors:
        # Fetch original patient data for form repopulation
        patient = await patient_crud_service.get_patient_by_icn(db, icn)

        return templates.TemplateResponse(
            "partials/patient_edit_form.html",
            {
                "request": request,
                "settings": settings,
                "patient": patient,
                "errors": errors,
                "data": patient_data
            }
        )

    # Update patient
    result = await patient_crud_service.update_patient(db, icn, patient_data)

    if not result["success"]:
        return f"""
        <div class="toast toast-error">Error: {result['error']}</div>
        """

    # Success: Return response that closes modal + shows toast + refreshes
    return f"""
    <div class="toast toast-success">Patient updated: {result['name_display']} ({result['icn']})</div>
    <script>
        closeModal();
        // Refresh either roster (if on dashboard) or reload page (if on detail page)
        if (document.querySelector('#roster-refresh-trigger')) {{
            document.querySelector('#roster-refresh-trigger').click();
        }} else {{
            window.location.reload();
        }}
    </script>
    """


@router.delete("/{icn}", response_class=HTMLResponse)
async def delete_patient(
    icn: str,
    db: AsyncSession = Depends(get_db),
    session_id: Optional[str] = Cookie(None, alias=settings.session.cookie_name)
):
    """
    Delete patient (hard delete with cascade to clinical data).
    If deleted patient is active CCOW context, clears the context.
    """
    # Validate session
    user_info = await validate_session(db, session_id) if session_id else None
    if not user_info:
        return """
        <div class="toast toast-error">Authentication required</div>
        """

    # Check if this patient is currently the active CCOW patient
    active_patient = await ccow_service.get_active_patient(session_id)
    is_active_patient = active_patient and active_patient.get("patient_id") == icn

    # Delete patient (cascades to all clinical data)
    result = await patient_crud_service.delete_patient(db, icn)

    if not result["success"]:
        return f"""
        <div class="toast toast-error">Error: {result['error']}</div>
        """

    # If deleted patient was active CCOW context, clear it
    if is_active_patient:
        try:
            await ccow_service.clear_active_patient(session_id)
            logger.info(f"Cleared CCOW context after deleting active patient: {icn}")
        except Exception as e:
            logger.error(f"Failed to clear CCOW context after patient deletion: {e}")
            # Don't fail the delete - patient is already gone

    # Success: Return response that shows toast + refreshes + redirects to dashboard if on detail page
    return f"""
    <div class="toast toast-success">Patient deleted: {icn}</div>
    <script>
        if (document.querySelector('#roster-refresh-trigger')) {{
            // On dashboard, just refresh table
            document.querySelector('#roster-refresh-trigger').click();
        }} else {{
            // On detail page, redirect to dashboard
            window.location.href = '/dashboard';
        }}
    </script>
    """


@router.get("/roster-table", response_class=HTMLResponse)
async def get_roster_table(
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_id: Optional[str] = Cookie(None, alias=settings.session.cookie_name)
):
    """
    Return refreshed patient roster table (for HTMX swap after CRUD operations).
    """
    # Validate session
    user_info = await validate_session(db, session_id) if session_id else None
    if not user_info:
        return """
        <p>Authentication required</p>
        """

    # Fetch patients (same query as dashboard)
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

    patients = [dict(row._mapping) for row in result.fetchall()]

    return templates.TemplateResponse(
        "partials/patient_roster_table.html",
        {
            "request": request,
            "settings": settings,
            "patients": patients
        }
    )
