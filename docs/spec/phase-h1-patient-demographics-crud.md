# Phase H.1: Patient Demographics CRUD

**Document Version:** v1.0  
**Created:** 2026-01-29  
**Status:** Ready for Implementation  
**Estimated Time:** 6-8 hours  

**Prerequisites:**
- Phases E, F, G complete (Sections 10.1, 10.2, 10.3)
- Monitoring Dashboard complete
- Dashboard Enhancement complete (Section 10.4)

**Next Phase:** After completing H.1, Phase H.2 (Vitals CRUD) will be implemented following the same pattern documented in `phase-h2-vitals-crud.md`.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Patterns](#architecture-patterns)
3. [Learning: Modal Dialog Implementation with HTMX](#learning-modal-dialog-implementation-with-htmx)
4. [Learning: Auto-Generating ICN (999 Series)](#learning-auto-generating-icn-999-series)
5. [Learning: Form Validation (Client + Server)](#learning-form-validation-client--server)
6. [Implementation Steps](#implementation-steps)
   - [Step H.1.1: Create Patient CRUD Service Layer](#step-h11-create-patient-crud-service-layer)
   - [Step H.1.2: Create Patient CRUD Routes](#step-h12-create-patient-crud-routes)
   - [Step H.1.3: Update Dashboard Template](#step-h13-update-dashboard-template)
   - [Step H.1.4: Update Patient Detail Template](#step-h14-update-patient-detail-template)
   - [Step H.1.5: Create Patient Roster Table Partial](#step-h15-create-patient-roster-table-partial)
   - [Step H.1.6: Create Patient Create Form Partial](#step-h16-create-patient-create-form-partial)
   - [Step H.1.7: Create Patient Edit Form Partial](#step-h17-create-patient-edit-form-partial)
   - [Step H.1.8: Add Modal, Toast, and Form CSS](#step-h18-add-modal-toast-and-form-css)
   - [Step H.1.9: Add JavaScript Functions](#step-h19-add-javascript-functions)
7. [Verification Steps](#verification-steps)
8. [Troubleshooting](#troubleshooting)
9. [Summary](#summary)

---

## Overview

---

### Overview

Phase H.1 introduces **Create, Read, Update, Delete (CRUD)** capabilities for patient demographics. Users can:
- **Create** new patients from dashboard via "Add New Patient" button
- **Edit** patient demographics from patient detail page
- **Delete** patients with confirmation dialog
- View immediate feedback via toast notifications

**Key Features:**
- Modal dialog-based forms (no page navigation)
- All demographics fields editable (26 fields total)
- Client-side and server-side validation
- Toast notifications for success/error feedback
- HTMX-powered dynamic updates (no full page reloads)
- Hard delete with JavaScript confirmation
- Auto-generated ICN for new patients (999 series)

**Future Implementation Note:**
After Phase H.1 is complete and tested, Phase H.2 (Vitals CRUD) will be implemented in Section 10.6, followed by:
- Phase H.3: Allergies CRUD
- Phase H.4: Medications CRUD
- Phase H.5: Clinical Notes CRUD

These will follow the same patterns established in H.1 and H.2.

---

### Architecture Patterns

#### Modal Dialog Pattern

All CRUD forms use modal dialogs that:
1. Overlay the current page (no navigation)
2. Load form HTML via HTMX from server
3. Submit via HTMX POST/PUT/DELETE
4. Close automatically on success
5. Display inline validation errors on failure

**Benefits:**
- Maintains user context (no losing place on page)
- Fast interaction (no page reloads)
- Consistent UX across all CRUD operations

#### Toast Notification Pattern

Success and error messages display as toast notifications:
- **Position:** Top of main content area, below CCOW banner
- **Duration:** 3 seconds auto-dismiss
- **Styling:** Green (success), Red (error), with teal border
- **Implementation:** Custom CSS + JavaScript (no external library)

#### HTMX Refresh Pattern

After successful CRUD operations:
- **Dashboard:** HTMX refreshes entire patient roster table
- **Patient Detail:** Browser reloads page to show updated demographics

This provides immediate visual feedback without full page reload.

#### CCOW Integration Pattern

Following industry best practices:
- **Create patient (Dashboard):** No CCOW context change (user creating, not viewing)
- **Edit patient (Detail Page):** Context already correct (user on detail page)
- **Delete patient:** Context cleared if deleted patient was active

---

### Learning: Modal Dialog Implementation with HTMX

**What is a Modal Dialog?**

A modal is an overlay window that:
- Appears on top of the current page
- Dims the background (backdrop)
- Captures user focus until closed
- Blocks interaction with underlying page

**HTMX Modal Pattern:**

```html
<!-- Button that triggers modal -->
<button hx-get="/patient/create-form"
        hx-target="#modal-container"
        hx-swap="innerHTML">
    Add New Patient
</button>

<!-- Modal container (empty until HTMX fills it) -->
<div id="modal-container"></div>
```

**Server returns modal HTML:**
```html
<div class="modal-backdrop" onclick="closeModal()">
    <div class="modal-dialog" onclick="event.stopPropagation()">
        <form hx-post="/patient/create" hx-target="#modal-container">
            <!-- Form fields here -->
        </form>
    </div>
</div>
```

**Key HTMX Attributes:**
- `hx-get` - Load modal content from server
- `hx-post` - Submit form to server
- `hx-target` - Where to put response (modal container)
- `hx-swap` - How to insert response (innerHTML replaces modal)

**Benefits:**
- Server-rendered forms (no client-side template)
- Validation errors rendered server-side
- Success closes modal + refreshes data
- Clean separation of concerns

---

### Learning: Auto-Generating ICN (999 Series)

**ICN Format:** `ICN` + 6-digit number (e.g., `ICN999001`, `ICN999002`)

**Why 999 Series?**
- med-z4 creates test/demo patients
- CDWWork historical patients use 100xxx series
- 999 series clearly identifies med-z4-created patients
- Prevents collision with real patient data

**Strategy:**
1. Query database for max ICN in 999 series
2. Extract numeric portion
3. Increment by 1
4. Format as `ICN` + zero-padded 6-digit number

**SQL Query:**
```sql
SELECT MAX(icn) FROM clinical.patient_demographics
WHERE icn LIKE 'ICN999%'
```

**Python Logic:**
```python
max_icn_result = await db.execute(text(
    "SELECT MAX(icn) FROM clinical.patient_demographics WHERE icn LIKE 'ICN999%'"
))
max_icn = max_icn_result.scalar()

if max_icn:
    # Extract number: "ICN999042" -> 999042
    current_num = int(max_icn.replace("ICN", ""))
    next_num = current_num + 1
else:
    # First patient in 999 series
    next_num = 999001

new_icn = f"ICN{next_num:06d}"  # Zero-pad to 6 digits
```

**Edge Cases:**
- No existing 999 patients → Start at ICN999001
- Max is ICN999999 → Error (series full, would need new series)

---

### Learning: Form Validation (Client + Server)

**Two-Layer Validation:**

1. **Client-side (HTML5):** Immediate feedback, no server round-trip
   ```html
   <input type="text" name="name_first" required maxlength="50">
   <input type="date" name="dob" required>
   <input type="tel" name="phone_primary" pattern="[0-9]{3}-[0-9]{3}-[0-9]{4}">
   ```

2. **Server-side (Python):** Security + business rules
   ```python
   def validate_patient_data(data: dict) -> dict:
       errors = {}

       if not data.get("name_last"):
           errors["name_last"] = "Last name is required"

       if data.get("dob"):
           dob = datetime.fromisoformat(data["dob"])
           if dob > datetime.now():
               errors["dob"] = "Date of birth cannot be in the future"

       return errors
   ```

**Validation Rules (Phase H.1):**
- **Required (from schema NOT NULL):** name_last, name_first, dob, sex, icn, patient_key
- **Format validation:**
  - SSN: ###-##-####
  - Phone: ###-###-####
  - ZIP: ##### or #####-####
  - State: 2-letter abbreviation
- **Range validation:**
  - DOB: Must be in past, age 0-150
  - Death date: Must be after DOB, cannot be in future
  - Service connected: 0-100
- **Business rules:**
  - If deceased_flag = 'Y', death_date should be provided
  - SSN last 4 should match last 4 of full SSN (if both provided)

**Error Display:**
- Client errors: HTML5 native browser tooltips
- Server errors: Red text inline below each field

---

### Implementation Steps

---

### Step H.1.1: Create Patient CRUD Service Layer

**File:** `app/services/patient_crud_service.py` (NEW FILE)

**Purpose:** Encapsulates all patient demographics CRUD business logic.

**Copy/paste the following code:**

```python
# -----------------------------------------------------------
# app/services/patient_crud_service.py
# -----------------------------------------------------------
# Patient demographics CRUD operations service
# -----------------------------------------------------------

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


async def generate_next_icn(db: AsyncSession) -> str:
    """
    Generate next available ICN in the 999 series.
    Returns ICN in format: ICN999001, ICN999002, etc.
    """
    try:
        result = await db.execute(text(
            "SELECT MAX(icn) FROM clinical.patient_demographics WHERE icn LIKE 'ICN999%'"
        ))
        max_icn = result.scalar()

        if max_icn:
            # Extract number: "ICN999042" -> 999042
            current_num = int(max_icn.replace("ICN", ""))
            next_num = current_num + 1
        else:
            # First patient in 999 series
            next_num = 999001

        # Check if we've exhausted the series
        if next_num > 999999:
            raise ValueError("ICN 999 series exhausted (max: ICN999999)")

        return f"ICN{next_num:06d}"

    except Exception as e:
        logger.error(f"Error generating ICN: {e}")
        raise


async def create_patient(db: AsyncSession, patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new patient record.
    Auto-generates ICN, patient_key, name_display, age, and timestamps.
    """
    try:
        # Generate ICN
        icn = await generate_next_icn(db)

        # Calculate age from DOB
        age = None
        if patient_data.get("dob"):
            dob = datetime.fromisoformat(patient_data["dob"])
            today = datetime.now()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        # Generate name_display
        name_last = patient_data.get("name_last", "")
        name_first = patient_data.get("name_first", "")
        name_display = f"{name_last.upper()}, {name_first.capitalize()}" if name_last and name_first else ""

        # Extract last 4 of SSN if full SSN provided
        ssn_last4 = patient_data.get("ssn_last4")
        if not ssn_last4 and patient_data.get("ssn"):
            ssn_last4 = patient_data["ssn"].replace("-", "")[-4:]

        # Prepare INSERT statement
        insert_query = text("""
            INSERT INTO clinical.patient_demographics (
                patient_key, icn, ssn, ssn_last4,
                name_last, name_first, name_display,
                dob, age, sex,
                primary_station, primary_station_name,
                address_street1, address_street2, address_city, address_state, address_zip,
                phone_primary, insurance_company_name,
                marital_status, religion, service_connected_percent,
                deceased_flag, death_date,
                source_system, last_updated
            ) VALUES (
                :patient_key, :icn, :ssn, :ssn_last4,
                :name_last, :name_first, :name_display,
                :dob, :age, :sex,
                :primary_station, :primary_station_name,
                :address_street1, :address_street2, :address_city, :address_state, :address_zip,
                :phone_primary, :insurance_company_name,
                :marital_status, :religion, :service_connected_percent,
                :deceased_flag, :death_date,
                :source_system, :last_updated
            )
        """)

        # Execute insert
        await db.execute(insert_query, {
            "patient_key": icn,  # patient_key same as ICN
            "icn": icn,
            "ssn": patient_data.get("ssn"),
            "ssn_last4": ssn_last4,
            "name_last": name_last,
            "name_first": name_first,
            "name_display": name_display,
            "dob": patient_data.get("dob"),
            "age": age,
            "sex": patient_data.get("sex"),
            "primary_station": patient_data.get("primary_station"),
            "primary_station_name": patient_data.get("primary_station_name"),
            "address_street1": patient_data.get("address_street1"),
            "address_street2": patient_data.get("address_street2"),
            "address_city": patient_data.get("address_city"),
            "address_state": patient_data.get("address_state"),
            "address_zip": patient_data.get("address_zip"),
            "phone_primary": patient_data.get("phone_primary"),
            "insurance_company_name": patient_data.get("insurance_company_name"),
            "marital_status": patient_data.get("marital_status"),
            "religion": patient_data.get("religion"),
            "service_connected_percent": patient_data.get("service_connected_percent"),
            "deceased_flag": patient_data.get("deceased_flag"),
            "death_date": patient_data.get("death_date"),
            "source_system": "med-z4",
            "last_updated": datetime.now(timezone.utc)
        })

        await db.commit()

        return {
            "success": True,
            "icn": icn,
            "name_display": name_display
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating patient: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def update_patient(db: AsyncSession, icn: str, patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update existing patient record.
    Recalculates age and name_display if relevant fields changed.
    """
    try:
        # Calculate age from DOB if provided
        age = None
        if patient_data.get("dob"):
            dob = datetime.fromisoformat(patient_data["dob"])
            today = datetime.now()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        # Generate name_display if name fields provided
        name_display = None
        if patient_data.get("name_last") and patient_data.get("name_first"):
            name_last = patient_data["name_last"]
            name_first = patient_data["name_first"]
            name_display = f"{name_last.upper()}, {name_first.capitalize()}"

        # Extract last 4 of SSN if full SSN provided
        ssn_last4 = patient_data.get("ssn_last4")
        if not ssn_last4 and patient_data.get("ssn"):
            ssn_last4 = patient_data["ssn"].replace("-", "")[-4:]

        # Build UPDATE statement dynamically based on provided fields
        update_fields = []
        params = {"icn": icn}

        for field in ["ssn", "name_last", "name_first", "dob", "sex",
                      "primary_station", "primary_station_name",
                      "address_street1", "address_street2", "address_city", "address_state", "address_zip",
                      "phone_primary", "insurance_company_name",
                      "marital_status", "religion", "service_connected_percent",
                      "deceased_flag", "death_date"]:
            if field in patient_data:
                update_fields.append(f"{field} = :{field}")
                params[field] = patient_data[field]

        # Add calculated/derived fields
        if age is not None:
            update_fields.append("age = :age")
            params["age"] = age

        if name_display is not None:
            update_fields.append("name_display = :name_display")
            params["name_display"] = name_display

        if ssn_last4:
            update_fields.append("ssn_last4 = :ssn_last4")
            params["ssn_last4"] = ssn_last4

        # Always update last_updated
        update_fields.append("last_updated = :last_updated")
        params["last_updated"] = datetime.now(timezone.utc)

        if not update_fields:
            return {"success": False, "error": "No fields to update"}

        update_query = text(f"""
            UPDATE clinical.patient_demographics
            SET {", ".join(update_fields)}
            WHERE icn = :icn
        """)

        result = await db.execute(update_query, params)
        await db.commit()

        if result.rowcount == 0:
            return {"success": False, "error": "Patient not found"}

        return {
            "success": True,
            "icn": icn,
            "name_display": name_display or "Patient"
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating patient {icn}: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def delete_patient(db: AsyncSession, icn: str) -> Dict[str, Any]:
    """
    Hard delete patient record.
    WARNING: This permanently removes the patient from the database.
    """
    try:
        delete_query = text("""
            DELETE FROM clinical.patient_demographics
            WHERE icn = :icn
        """)

        result = await db.execute(delete_query, {"icn": icn})
        await db.commit()

        if result.rowcount == 0:
            return {"success": False, "error": "Patient not found"}

        logger.info(f"Patient deleted: {icn}")

        return {"success": True, "icn": icn}

    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting patient {icn}: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def get_patient_by_icn(db: AsyncSession, icn: str) -> Optional[Dict[str, Any]]:
    """
    Fetch single patient by ICN for edit form population.
    """
    try:
        query = text("""
            SELECT * FROM clinical.patient_demographics
            WHERE icn = :icn
        """)

        result = await db.execute(query, {"icn": icn})
        row = result.fetchone()

        if not row:
            return None

        # Convert row to dict
        return dict(row._mapping)

    except Exception as e:
        logger.error(f"Error fetching patient {icn}: {e}")
        return None


def validate_patient_data(data: Dict[str, Any], is_create: bool = True) -> Dict[str, str]:
    """
    Validate patient data.
    Returns dict of field errors (empty if valid).
    """
    errors = {}

    # Required fields (based on database schema NOT NULL constraints)
    if is_create or "name_last" in data:
        if not data.get("name_last"):
            errors["name_last"] = "Last name is required"

    if is_create or "name_first" in data:
        if not data.get("name_first"):
            errors["name_first"] = "First name is required"

    if is_create or "dob" in data:
        if not data.get("dob"):
            errors["dob"] = "Date of birth is required"
        else:
            try:
                dob = datetime.fromisoformat(data["dob"])
                if dob > datetime.now():
                    errors["dob"] = "Date of birth cannot be in the future"

                # Check reasonable age range
                age = datetime.now().year - dob.year
                if age < 0 or age > 150:
                    errors["dob"] = "Date of birth results in unreasonable age"
            except ValueError:
                errors["dob"] = "Invalid date format"

    if is_create or "sex" in data:
        if not data.get("sex"):
            errors["sex"] = "Sex is required"
        elif data["sex"] not in ["M", "F"]:
            errors["sex"] = "Sex must be M or F"

    # Format validations (if provided)
    if data.get("ssn"):
        ssn = data["ssn"]
        if len(ssn) != 11 or ssn[3] != "-" or ssn[6] != "-":
            errors["ssn"] = "SSN must be in format ###-##-####"

    if data.get("phone_primary"):
        phone = data["phone_primary"]
        if len(phone) != 12 or phone[3] != "-" or phone[7] != "-":
            errors["phone_primary"] = "Phone must be in format ###-###-####"

    if data.get("address_zip"):
        zip_code = data["address_zip"]
        if not (len(zip_code) == 5 or (len(zip_code) == 10 and zip_code[5] == "-")):
            errors["address_zip"] = "ZIP must be ##### or #####-####"

    if data.get("address_state"):
        state = data["address_state"]
        if len(state) != 2 or not state.isupper():
            errors["address_state"] = "State must be 2-letter abbreviation (e.g., GA, CA)"

    if data.get("service_connected_percent"):
        try:
            percent = float(data["service_connected_percent"])
            if percent < 0 or percent > 100:
                errors["service_connected_percent"] = "Service connected percent must be 0-100"
        except ValueError:
            errors["service_connected_percent"] = "Must be a number"

    if data.get("death_date"):
        if not data.get("dob"):
            # Can't validate without DOB
            pass
        else:
            try:
                death_date = datetime.fromisoformat(data["death_date"])
                dob = datetime.fromisoformat(data["dob"])
                if death_date < dob:
                    errors["death_date"] = "Death date cannot be before birth date"
                if death_date > datetime.now():
                    errors["death_date"] = "Death date cannot be in the future"
            except ValueError:
                errors["death_date"] = "Invalid date format"

    return errors
```

**Verification:**
```bash
python -c "from app.services.patient_crud_service import generate_next_icn; print('Service imported successfully')"
```

---

### Step H.1.2: Create Patient CRUD Routes

**File:** `app/routes/patient_crud.py` (NEW FILE)

**Purpose:** HTTP route handlers for patient CRUD operations.

**Copy/paste the following code:**

```python
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

from database import get_db
from app.services.auth_service import validate_session
from app.services import patient_crud_service
from config import settings

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
    Delete patient (hard delete).
    """
    # Validate session
    user_info = await validate_session(db, session_id) if session_id else None
    if not user_info:
        return """
        <div class="toast toast-error">Authentication required</div>
        """

    # Delete patient
    result = await patient_crud_service.delete_patient(db, icn)

    if not result["success"]:
        return f"""
        <div class="toast toast-error">Error: {result['error']}</div>
        """

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
```

**Register Router in `app/main.py`:**

Find the section where routers are imported:
```python
from app.routes import auth, dashboard, admin, health, patient, monitoring
```

Add `patient_crud`:
```python
from app.routes import auth, dashboard, admin, health, patient, monitoring, patient_crud
```

Find the section where routers are registered:
```python
app.include_router(monitoring.router, tags=["monitoring"])
```

Add after:
```python
app.include_router(patient_crud.router, tags=["patient-crud"])
```

---

### Step H.1.3: Update Dashboard Template

**File:** `app/templates/dashboard.html`

**Goal:** Add "Add New Patient" button and modal container.

**Find** the patient roster heading (around line 30):
```html
    <h2 class="section-title">Patient Roster</h2>
```

**Replace with:**
```html
    <div class="section-header-with-action">
        <h2 class="section-title">Patient Roster</h2>
        <button hx-get="/patient/create-form"
                hx-target="#modal-container"
                hx-swap="innerHTML"
                class="btn btn-primary">
            Add New Patient
        </button>
    </div>
```

**Find** the end of the patient roster table (after `</table>`):
```html
            </table>
        </div>

        <p style="margin-top: 1rem; color: var(--color-text-muted);">
            Showing {{ patients|length }} patients
        </p>
```

**Add after the "Showing X patients" paragraph:**
```html
        <!-- Hidden button for HTMX to refresh roster table -->
        <button id="roster-refresh-trigger"
                hx-get="/patient/roster-table"
                hx-target="#roster-table-container"
                hx-swap="innerHTML"
                style="display: none;">
        </button>
```

**Find** the roster table opening tag:
```html
        <div class="table-container">
            <table class="data-table">
```

**Wrap the table in a container div:**
```html
        <div id="roster-table-container">
            <div class="table-container">
                <table class="data-table">
```

**And find the closing** `</div>` after `</table>`:
```html
                </table>
            </div>
        </div>  <!-- closes roster-table-container -->
```

**Find** the very end of the template, before `{% endblock %}`:

**Add:**
```html
    <!-- Modal container for CRUD forms -->
    <div id="modal-container"></div>

    <!-- Toast container for notifications -->
    <div id="toast-container"></div>
{% endblock %}
```

---

### Step H.1.4: Update Patient Detail Template

**File:** `app/templates/patient_detail.html`

**Goal:** Add "Edit Patient" and "Delete Patient" buttons to patient detail page.

**Find** the patient header section (after patient name/ICN display, before clinical sections):
```html
        <p><strong>Sex:</strong> {{ patient.sex or 'Unknown' }}</p>
        <p><strong>Primary Station:</strong> {{ patient.primary_station or 'Unknown' }}</p>
    </section>
```

**Add after this section:**
```html
    <!-- Patient Actions -->
    <div class="patient-actions" style="margin: 1rem 0;">
        <button hx-get="/patient/{{ patient.icn }}/edit-form"
                hx-target="#modal-container"
                hx-swap="innerHTML"
                class="btn btn-outline">
            Edit Patient
        </button>

        <button onclick="confirmDeletePatient('{{ patient.icn }}', '{{ patient.name_display }}')"
                class="btn btn-danger">
            Delete Patient
        </button>
    </div>
```

**Find** the end of the template, before `{% endblock %}`:

**Add:**
```html
    <!-- Modal container for edit form -->
    <div id="modal-container"></div>

    <!-- Toast container for notifications -->
    <div id="toast-container"></div>
{% endblock %}
```

---

### Step H.1.5: Create Patient Roster Table Partial

**File:** `app/templates/partials/patient_roster_table.html` (NEW FILE)

**Purpose:** Table HTML that can be swapped via HTMX after CRUD operations.

**Copy/paste the following:**

```html
<div class="table-container">
    <table class="data-table">
        <thead>
            <tr>
                <th>Name</th>
                <th>ICN</th>
                <th>DOB</th>
                <th>Age</th>
                <th>Sex</th>
                <th>SSN</th>
                <th>Station</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for patient in patients %}
            <tr id="patient-row-{{ patient.icn }}"
                {% if active_patient_icn == patient.icn %}class="patient-selected"{% endif %}>
                <td>{{ patient.name_display }}</td>
                <td>{{ patient.icn }}</td>
                <td>{{ patient.dob.strftime('%Y-%m-%d') if patient.dob else 'Unknown' }}</td>
                <td>{{ patient.age if patient.age is not none else '—' }}</td>
                <td>{{ patient.sex or '—' }}</td>
                <td>{{ patient.ssn_last4 or '—' }}</td>
                <td>{{ patient.primary_station or '—' }}</td>
                <td>
                    <a href="/patient/{{ patient.icn }}" class="btn-sm">View</a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
```

---

### Step H.1.6: Create Patient Create Form Partial

**File:** `app/templates/partials/patient_create_form.html` (NEW FILE)

**Purpose:** Modal form for creating new patient.

**Copy/paste the following:**

```html
<div class="modal-backdrop" onclick="closeModal()">
    <div class="modal-dialog" onclick="event.stopPropagation()">
        <div class="modal-header">
            <h3>Add New Patient</h3>
            <button onclick="closeModal()" class="btn-close">&times;</button>
        </div>

        <form hx-post="/patient/create"
              hx-target="#modal-container"
              hx-swap="innerHTML"
              class="modal-form">

            <!-- Required Fields -->
            <fieldset>
                <legend>Required Information</legend>

                <div class="form-row">
                    <div class="form-group">
                        <label for="name_last">Last Name *</label>
                        <input type="text"
                               id="name_last"
                               name="name_last"
                               value="{{ data.name_last if data else '' }}"
                               required
                               maxlength="50">
                        {% if errors and errors.name_last %}
                        <span class="error-text">{{ errors.name_last }}</span>
                        {% endif %}
                    </div>

                    <div class="form-group">
                        <label for="name_first">First Name *</label>
                        <input type="text"
                               id="name_first"
                               name="name_first"
                               value="{{ data.name_first if data else '' }}"
                               required
                               maxlength="50">
                        {% if errors and errors.name_first %}
                        <span class="error-text">{{ errors.name_first }}</span>
                        {% endif %}
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="dob">Date of Birth *</label>
                        <input type="date"
                               id="dob"
                               name="dob"
                               value="{{ data.dob if data else '' }}"
                               required>
                        {% if errors and errors.dob %}
                        <span class="error-text">{{ errors.dob }}</span>
                        {% endif %}
                    </div>

                    <div class="form-group">
                        <label for="sex">Sex *</label>
                        <select id="sex" name="sex" required>
                            <option value="">Select...</option>
                            <option value="M" {% if data and data.sex == 'M' %}selected{% endif %}>Male</option>
                            <option value="F" {% if data and data.sex == 'F' %}selected{% endif %}>Female</option>
                        </select>
                        {% if errors and errors.sex %}
                        <span class="error-text">{{ errors.sex }}</span>
                        {% endif %}
                    </div>
                </div>
            </fieldset>

            <!-- Identification -->
            <fieldset>
                <legend>Identification</legend>

                <div class="form-row">
                    <div class="form-group">
                        <label for="ssn">SSN</label>
                        <input type="text"
                               id="ssn"
                               name="ssn"
                               value="{{ data.ssn if data else '' }}"
                               placeholder="###-##-####"
                               pattern="[0-9]{3}-[0-9]{2}-[0-9]{4}"
                               maxlength="11">
                        <small>Format: ###-##-####</small>
                        {% if errors and errors.ssn %}
                        <span class="error-text">{{ errors.ssn }}</span>
                        {% endif %}
                    </div>
                </div>
            </fieldset>

            <!-- Station Information -->
            <fieldset>
                <legend>Station</legend>

                <div class="form-row">
                    <div class="form-group">
                        <label for="primary_station">Primary Station</label>
                        <input type="text"
                               id="primary_station"
                               name="primary_station"
                               value="{{ data.primary_station if data else '' }}"
                               placeholder="508"
                               maxlength="10">
                    </div>

                    <div class="form-group">
                        <label for="primary_station_name">Station Name</label>
                        <input type="text"
                               id="primary_station_name"
                               name="primary_station_name"
                               value="{{ data.primary_station_name if data else '' }}"
                               placeholder="Atlanta VA Medical Center"
                               maxlength="100">
                    </div>
                </div>
            </fieldset>

            <!-- Address -->
            <fieldset>
                <legend>Address</legend>

                <div class="form-group">
                    <label for="address_street1">Street Address 1</label>
                    <input type="text"
                           id="address_street1"
                           name="address_street1"
                           value="{{ data.address_street1 if data else '' }}"
                           maxlength="100">
                </div>

                <div class="form-group">
                    <label for="address_street2">Street Address 2</label>
                    <input type="text"
                           id="address_street2"
                           name="address_street2"
                           value="{{ data.address_street2 if data else '' }}"
                           maxlength="100">
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="address_city">City</label>
                        <input type="text"
                               id="address_city"
                               name="address_city"
                               value="{{ data.address_city if data else '' }}"
                               maxlength="50">
                    </div>

                    <div class="form-group">
                        <label for="address_state">State</label>
                        <input type="text"
                               id="address_state"
                               name="address_state"
                               value="{{ data.address_state if data else '' }}"
                               placeholder="GA"
                               maxlength="2"
                               pattern="[A-Z]{2}">
                        <small>2-letter code (e.g., GA, CA)</small>
                        {% if errors and errors.address_state %}
                        <span class="error-text">{{ errors.address_state }}</span>
                        {% endif %}
                    </div>

                    <div class="form-group">
                        <label for="address_zip">ZIP Code</label>
                        <input type="text"
                               id="address_zip"
                               name="address_zip"
                               value="{{ data.address_zip if data else '' }}"
                               placeholder="#####"
                               maxlength="10">
                        <small>##### or #####-####</small>
                        {% if errors and errors.address_zip %}
                        <span class="error-text">{{ errors.address_zip }}</span>
                        {% endif %}
                    </div>
                </div>
            </fieldset>

            <!-- Contact & Insurance -->
            <fieldset>
                <legend>Contact & Insurance</legend>

                <div class="form-row">
                    <div class="form-group">
                        <label for="phone_primary">Phone</label>
                        <input type="tel"
                               id="phone_primary"
                               name="phone_primary"
                               value="{{ data.phone_primary if data else '' }}"
                               placeholder="###-###-####"
                               pattern="[0-9]{3}-[0-9]{3}-[0-9]{4}"
                               maxlength="12">
                        <small>Format: ###-###-####</small>
                        {% if errors and errors.phone_primary %}
                        <span class="error-text">{{ errors.phone_primary }}</span>
                        {% endif %}
                    </div>

                    <div class="form-group">
                        <label for="insurance_company_name">Insurance Company</label>
                        <input type="text"
                               id="insurance_company_name"
                               name="insurance_company_name"
                               value="{{ data.insurance_company_name if data else '' }}"
                               maxlength="100">
                    </div>
                </div>
            </fieldset>

            <!-- Additional Information -->
            <fieldset>
                <legend>Additional Information</legend>

                <div class="form-row">
                    <div class="form-group">
                        <label for="marital_status">Marital Status</label>
                        <select id="marital_status" name="marital_status">
                            <option value="">Select...</option>
                            <option value="Single" {% if data and data.marital_status == 'Single' %}selected{% endif %}>Single</option>
                            <option value="Married" {% if data and data.marital_status == 'Married' %}selected{% endif %}>Married</option>
                            <option value="Divorced" {% if data and data.marital_status == 'Divorced' %}selected{% endif %}>Divorced</option>
                            <option value="Widowed" {% if data and data.marital_status == 'Widowed' %}selected{% endif %}>Widowed</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="religion">Religion</label>
                        <input type="text"
                               id="religion"
                               name="religion"
                               value="{{ data.religion if data else '' }}"
                               maxlength="50">
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="service_connected_percent">Service Connected %</label>
                        <input type="number"
                               id="service_connected_percent"
                               name="service_connected_percent"
                               value="{{ data.service_connected_percent if data else '' }}"
                               min="0"
                               max="100"
                               step="10">
                        {% if errors and errors.service_connected_percent %}
                        <span class="error-text">{{ errors.service_connected_percent }}</span>
                        {% endif %}
                    </div>
                </div>
            </fieldset>

            <!-- Deceased Information -->
            <fieldset>
                <legend>Deceased Information (if applicable)</legend>

                <div class="form-row">
                    <div class="form-group">
                        <label for="deceased_flag">Deceased</label>
                        <select id="deceased_flag" name="deceased_flag">
                            <option value="">Select...</option>
                            <option value="N" {% if data and data.deceased_flag == 'N' %}selected{% endif %}>No</option>
                            <option value="Y" {% if data and data.deceased_flag == 'Y' %}selected{% endif %}>Yes</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="death_date">Death Date</label>
                        <input type="date"
                               id="death_date"
                               name="death_date"
                               value="{{ data.death_date if data else '' }}">
                        {% if errors and errors.death_date %}
                        <span class="error-text">{{ errors.death_date }}</span>
                        {% endif %}
                    </div>
                </div>
            </fieldset>

            <div class="modal-footer">
                <button type="button" onclick="closeModal()" class="btn btn-secondary">Cancel</button>
                <button type="submit" class="btn btn-primary">Create Patient</button>
            </div>
        </form>
    </div>
</div>
```

---

### Step H.1.7: Create Patient Edit Form Partial

**File:** `app/templates/partials/patient_edit_form.html` (NEW FILE)

**Purpose:** Modal form for editing existing patient (pre-populated with current data).

**Copy/paste the following:**

```html
<div class="modal-backdrop" onclick="closeModal()">
    <div class="modal-dialog" onclick="event.stopPropagation()">
        <div class="modal-header">
            <h3>Edit Patient: {{ patient.name_display }} ({{ patient.icn }})</h3>
            <button onclick="closeModal()" class="btn-close">&times;</button>
        </div>

        <form hx-post="/patient/{{ patient.icn }}/update"
              hx-target="#modal-container"
              hx-swap="innerHTML"
              class="modal-form">

            <!-- ICN Display (Read-only) -->
            <fieldset>
                <legend>Patient Identity</legend>
                <div class="form-group">
                    <label>ICN (Read-only)</label>
                    <input type="text"
                           value="{{ patient.icn }}"
                           readonly
                           class="readonly-field">
                    <small>ICN cannot be changed</small>
                </div>
            </fieldset>

            <!-- Required Fields -->
            <fieldset>
                <legend>Required Information</legend>

                <div class="form-row">
                    <div class="form-group">
                        <label for="name_last">Last Name *</label>
                        <input type="text"
                               id="name_last"
                               name="name_last"
                               value="{{ data.name_last if data else patient.name_last }}"
                               required
                               maxlength="50">
                        {% if errors and errors.name_last %}
                        <span class="error-text">{{ errors.name_last }}</span>
                        {% endif %}
                    </div>

                    <div class="form-group">
                        <label for="name_first">First Name *</label>
                        <input type="text"
                               id="name_first"
                               name="name_first"
                               value="{{ data.name_first if data else patient.name_first }}"
                               required
                               maxlength="50">
                        {% if errors and errors.name_first %}
                        <span class="error-text">{{ errors.name_first }}</span>
                        {% endif %}
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="dob">Date of Birth *</label>
                        <input type="date"
                               id="dob"
                               name="dob"
                               value="{{ (data.dob if data else patient.dob.strftime('%Y-%m-%d')) if patient.dob else '' }}"
                               required>
                        {% if errors and errors.dob %}
                        <span class="error-text">{{ errors.dob }}</span>
                        {% endif %}
                    </div>

                    <div class="form-group">
                        <label for="sex">Sex *</label>
                        <select id="sex" name="sex" required>
                            <option value="">Select...</option>
                            <option value="M" {% if (data.sex if data else patient.sex) == 'M' %}selected{% endif %}>Male</option>
                            <option value="F" {% if (data.sex if data else patient.sex) == 'F' %}selected{% endif %}>Female</option>
                        </select>
                        {% if errors and errors.sex %}
                        <span class="error-text">{{ errors.sex }}</span>
                        {% endif %}
                    </div>
                </div>
            </fieldset>

            <!-- Identification -->
            <fieldset>
                <legend>Identification</legend>

                <div class="form-row">
                    <div class="form-group">
                        <label for="ssn">SSN</label>
                        <input type="text"
                               id="ssn"
                               name="ssn"
                               value="{{ data.ssn if data else (patient.ssn or '') }}"
                               placeholder="###-##-####"
                               pattern="[0-9]{3}-[0-9]{2}-[0-9]{4}"
                               maxlength="11">
                        <small>Format: ###-##-####</small>
                        {% if errors and errors.ssn %}
                        <span class="error-text">{{ errors.ssn }}</span>
                        {% endif %}
                    </div>
                </div>
            </fieldset>

            <!-- Station Information -->
            <fieldset>
                <legend>Station</legend>

                <div class="form-row">
                    <div class="form-group">
                        <label for="primary_station">Primary Station</label>
                        <input type="text"
                               id="primary_station"
                               name="primary_station"
                               value="{{ data.primary_station if data else (patient.primary_station or '') }}"
                               maxlength="10">
                    </div>

                    <div class="form-group">
                        <label for="primary_station_name">Station Name</label>
                        <input type="text"
                               id="primary_station_name"
                               name="primary_station_name"
                               value="{{ data.primary_station_name if data else (patient.primary_station_name or '') }}"
                               maxlength="100">
                    </div>
                </div>
            </fieldset>

            <!-- Address -->
            <fieldset>
                <legend>Address</legend>

                <div class="form-group">
                    <label for="address_street1">Street Address 1</label>
                    <input type="text"
                           id="address_street1"
                           name="address_street1"
                           value="{{ data.address_street1 if data else (patient.address_street1 or '') }}"
                           maxlength="100">
                </div>

                <div class="form-group">
                    <label for="address_street2">Street Address 2</label>
                    <input type="text"
                           id="address_street2"
                           name="address_street2"
                           value="{{ data.address_street2 if data else (patient.address_street2 or '') }}"
                           maxlength="100">
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="address_city">City</label>
                        <input type="text"
                               id="address_city"
                               name="address_city"
                               value="{{ data.address_city if data else (patient.address_city or '') }}"
                               maxlength="50">
                    </div>

                    <div class="form-group">
                        <label for="address_state">State</label>
                        <input type="text"
                               id="address_state"
                               name="address_state"
                               value="{{ data.address_state if data else (patient.address_state or '') }}"
                               maxlength="2"
                               pattern="[A-Z]{2}">
                        <small>2-letter code (e.g., GA, CA)</small>
                        {% if errors and errors.address_state %}
                        <span class="error-text">{{ errors.address_state }}</span>
                        {% endif %}
                    </div>

                    <div class="form-group">
                        <label for="address_zip">ZIP Code</label>
                        <input type="text"
                               id="address_zip"
                               name="address_zip"
                               value="{{ data.address_zip if data else (patient.address_zip or '') }}"
                               maxlength="10">
                        <small>##### or #####-####</small>
                        {% if errors and errors.address_zip %}
                        <span class="error-text">{{ errors.address_zip }}</span>
                        {% endif %}
                    </div>
                </div>
            </fieldset>

            <!-- Contact & Insurance -->
            <fieldset>
                <legend>Contact & Insurance</legend>

                <div class="form-row">
                    <div class="form-group">
                        <label for="phone_primary">Phone</label>
                        <input type="tel"
                               id="phone_primary"
                               name="phone_primary"
                               value="{{ data.phone_primary if data else (patient.phone_primary or '') }}"
                               pattern="[0-9]{3}-[0-9]{3}-[0-9]{4}"
                               maxlength="12">
                        <small>Format: ###-###-####</small>
                        {% if errors and errors.phone_primary %}
                        <span class="error-text">{{ errors.phone_primary }}</span>
                        {% endif %}
                    </div>

                    <div class="form-group">
                        <label for="insurance_company_name">Insurance Company</label>
                        <input type="text"
                               id="insurance_company_name"
                               name="insurance_company_name"
                               value="{{ data.insurance_company_name if data else (patient.insurance_company_name or '') }}"
                               maxlength="100">
                    </div>
                </div>
            </fieldset>

            <!-- Additional Information -->
            <fieldset>
                <legend>Additional Information</legend>

                <div class="form-row">
                    <div class="form-group">
                        <label for="marital_status">Marital Status</label>
                        <select id="marital_status" name="marital_status">
                            <option value="">Select...</option>
                            <option value="Single" {% if (data.marital_status if data else patient.marital_status) == 'Single' %}selected{% endif %}>Single</option>
                            <option value="Married" {% if (data.marital_status if data else patient.marital_status) == 'Married' %}selected{% endif %}>Married</option>
                            <option value="Divorced" {% if (data.marital_status if data else patient.marital_status) == 'Divorced' %}selected{% endif %}>Divorced</option>
                            <option value="Widowed" {% if (data.marital_status if data else patient.marital_status) == 'Widowed' %}selected{% endif %}>Widowed</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="religion">Religion</label>
                        <input type="text"
                               id="religion"
                               name="religion"
                               value="{{ data.religion if data else (patient.religion or '') }}"
                               maxlength="50">
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="service_connected_percent">Service Connected %</label>
                        <input type="number"
                               id="service_connected_percent"
                               name="service_connected_percent"
                               value="{{ data.service_connected_percent if data else (patient.service_connected_percent or '') }}"
                               min="0"
                               max="100"
                               step="10">
                        {% if errors and errors.service_connected_percent %}
                        <span class="error-text">{{ errors.service_connected_percent }}</span>
                        {% endif %}
                    </div>
                </div>
            </fieldset>

            <!-- Deceased Information -->
            <fieldset>
                <legend>Deceased Information (if applicable)</legend>

                <div class="form-row">
                    <div class="form-group">
                        <label for="deceased_flag">Deceased</label>
                        <select id="deceased_flag" name="deceased_flag">
                            <option value="">Select...</option>
                            <option value="N" {% if (data.deceased_flag if data else patient.deceased_flag) == 'N' %}selected{% endif %}>No</option>
                            <option value="Y" {% if (data.deceased_flag if data else patient.deceased_flag) == 'Y' %}selected{% endif %}>Yes</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="death_date">Death Date</label>
                        <input type="date"
                               id="death_date"
                               name="death_date"
                               value="{{ (data.death_date if data else patient.death_date.strftime('%Y-%m-%d')) if patient.death_date else '' }}">
                        {% if errors and errors.death_date %}
                        <span class="error-text">{{ errors.death_date }}</span>
                        {% endif %}
                    </div>
                </div>
            </fieldset>

            <div class="modal-footer">
                <button type="button" onclick="closeModal()" class="btn btn-secondary">Cancel</button>
                <button type="submit" class="btn btn-primary">Update Patient</button>
            </div>
        </form>
    </div>
</div>
```

---

### Step H.1.8: Add Modal, Toast, and Form CSS

**File:** `app/static/css/style.css`

**Add to the end of the file:**

```css
/* =====================================================
   Phase H.1: CRUD Modal, Toast, and Form Styles
   ===================================================== */

/* Section Header with Action Button */
.section-header-with-action {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-md);
}

/* Modal Backdrop */
.modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
    overflow-y: auto;
    padding: 2rem;
}

/* Modal Dialog */
.modal-dialog {
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    max-width: 800px;
    width: 100%;
    max-height: 90vh;
    overflow-y: auto;
    margin: auto;
}

/* Modal Header */
.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-lg);
    border-bottom: 1px solid var(--color-border);
    background-color: var(--color-bg-card);
}

.modal-header h3 {
    margin: 0;
    font-size: var(--font-size-xl);
    color: var(--color-text-primary);
}

.btn-close {
    background: none;
    border: none;
    font-size: 2rem;
    line-height: 1;
    color: var(--color-text-muted);
    cursor: pointer;
    padding: 0;
    width: 2rem;
    height: 2rem;
    display: flex;
    align-items: center;
    justify-content: center;
}

.btn-close:hover {
    color: var(--color-text-primary);
}

/* Modal Form */
.modal-form {
    padding: var(--spacing-lg);
}

.modal-form fieldset {
    border: 1px solid var(--color-border);
    border-radius: 6px;
    padding: var(--spacing-md);
    margin-bottom: var(--spacing-md);
}

.modal-form legend {
    font-weight: 600;
    font-size: var(--font-size-md);
    color: var(--color-primary);
    padding: 0 var(--spacing-sm);
}

.form-group {
    margin-bottom: var(--spacing-md);
    flex: 1;
}

.form-group label {
    display: block;
    margin-bottom: var(--spacing-xs);
    font-weight: 500;
    color: var(--color-text-primary);
}

.form-group input,
.form-group select,
.form-group textarea {
    width: 100%;
    padding: var(--spacing-sm);
    border: 1px solid var(--color-border);
    border-radius: 4px;
    font-size: var(--font-size-base);
    font-family: inherit;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.1);
}

.form-group input.readonly-field {
    background-color: var(--color-bg-page);
    color: var(--color-text-muted);
    cursor: not-allowed;
}

.form-group small {
    display: block;
    margin-top: var(--spacing-xs);
    font-size: 0.875rem;
    color: var(--color-text-muted);
}

.form-row {
    display: flex;
    gap: var(--spacing-md);
    margin-bottom: 0;
}

.form-row .form-group {
    margin-bottom: var(--spacing-md);
}

.error-text {
    display: block;
    margin-top: var(--spacing-xs);
    font-size: 0.875rem;
    color: #dc2626;
    font-weight: 500;
}

/* Modal Footer */
.modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: var(--spacing-sm);
    padding: var(--spacing-lg);
    border-top: 1px solid var(--color-border);
    background-color: var(--color-bg-card);
}

/* Toast Notifications */
#toast-container {
    position: fixed;
    top: 120px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 2000;
    width: 90%;
    max-width: 600px;
}

.toast {
    padding: var(--spacing-md);
    border-radius: 6px;
    margin-bottom: var(--spacing-sm);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    animation: slideDown 0.3s ease-out;
}

.toast-success {
    background-color: #d1fae5;
    border: 2px solid #10b981;
    color: #065f46;
}

.toast-error {
    background-color: #fee2e2;
    border: 2px solid #ef4444;
    color: #991b1b;
}

@keyframes slideDown {
    from {
        opacity: 0;
        transform: translateY(-20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* Patient Actions (on detail page) */
.patient-actions {
    display: flex;
    gap: var(--spacing-sm);
}

/* Button Variants */
.btn-danger {
    background-color: #ef4444;
    color: white;
    border: none;
}

.btn-danger:hover {
    background-color: #dc2626;
}

/* Responsive */
@media (max-width: 768px) {
    .modal-dialog {
        max-width: 100%;
        margin: 0;
        border-radius: 0;
        max-height: 100vh;
    }

    .form-row {
        flex-direction: column;
    }

    .modal-backdrop {
        padding: 0;
    }
}
```

---

### Step H.1.9: Add JavaScript Functions

**File:** `app/templates/base.html`

**Find** the closing `</body>` tag.

**Add before it:**

```html
    <!-- Phase H.1: CRUD JavaScript Functions -->
    <script>
        // Close modal dialog
        function closeModal() {
            const modalContainer = document.getElementById('modal-container');
            if (modalContainer) {
                modalContainer.innerHTML = '';
            }
        }

        // Show toast notification
        function showToast(message, type = 'success') {
            const toastContainer = document.getElementById('toast-container');
            if (!toastContainer) return;

            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.textContent = message;

            toastContainer.appendChild(toast);

            // Auto-dismiss after 3 seconds
            setTimeout(() => {
                toast.remove();
            }, 3000);
        }

        // Confirm patient deletion
        function confirmDeletePatient(icn, name) {
            if (confirm(`Are you sure you want to delete patient ${name} (${icn})?\n\nThis action cannot be undone.`)) {
                // Use HTMX to send DELETE request
                htmx.ajax('DELETE', `/patient/${icn}`, {
                    target: '#modal-container',
                    swap: 'innerHTML'
                });
            }
        }

        // Listen for toast messages in HTMX responses
        document.body.addEventListener('htmx:afterSwap', function(event) {
            // Check if response contains toast element
            const toast = event.detail.target.querySelector('.toast');
            if (toast) {
                // Move toast to toast container
                const toastContainer = document.getElementById('toast-container');
                if (toastContainer) {
                    toastContainer.appendChild(toast);

                    // Auto-dismiss after 3 seconds
                    setTimeout(() => {
                        toast.remove();
                    }, 3000);
                }
            }
        });

        // Close modal when pressing Escape key
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                closeModal();
            }
        });
    </script>
</body>
```

---

### Verification Steps

#### V1: Service Layer Import Test

```bash
python -c "from app.services.patient_crud_service import generate_next_icn, create_patient; print('✅ Patient CRUD service imports successfully')"
```

Expected: `✅ Patient CRUD service imports successfully`

---

#### V2: Application Startup Test

```bash
uvicorn app.main:app --reload --port 8005
```

Expected console output:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8005
```

Check for:
- ✅ No import errors
- ✅ Router registered: `patient-crud`

---

#### V3: Dashboard "Add New Patient" Button

1. Navigate to http://localhost:8005/dashboard
2. Login if not authenticated
3. Verify:
   - ✅ "Add New Patient" button visible (top-right, aligned with "Patient Roster" heading)
   - ✅ Button has teal background (primary color)

---

#### V4: Create Patient Modal

1. Click "Add New Patient"
2. Verify:
   - ✅ Modal dialog appears with semi-transparent backdrop
   - ✅ Form has 6 fieldsets: Required Information, Identification, Station, Address, Contact & Insurance, Additional Information, Deceased Information
   - ✅ Required fields marked with *
   - ✅ Close button (×) in top-right of modal

3. Click backdrop (outside modal)
   - ✅ Modal closes

---

#### V5: Create Patient - Success Flow

1. Click "Add New Patient"
2. Fill out required fields:
   - Last Name: `TESTPATIENT`
   - First Name: `Demo`
   - DOB: `1990-01-01`
   - Sex: `M`
3. Click "Create Patient"
4. Verify:
   - ✅ Toast notification appears: "Patient created: TESTPATIENT, Demo (ICN999001)"
   - ✅ Toast is green with teal border
   - ✅ Modal closes automatically
   - ✅ Patient roster table refreshes (new patient appears)
   - ✅ Toast disappears after 3 seconds

---

#### V6: Create Patient - Validation Errors

1. Click "Add New Patient"
2. Leave name fields empty, click "Create Patient"
3. Verify:
   - ✅ Modal does NOT close
   - ✅ Red error text appears below empty fields: "Last name is required", "First name is required"
4. Fill in invalid SSN: `123456789`
5. Click "Create Patient"
6. Verify:
   - ✅ Error: "SSN must be in format ###-##-####"

---

#### V7: Edit Patient from Detail Page

1. Navigate to patient detail page: http://localhost:8005/patient/ICN999001
2. Verify:
   - ✅ "Edit Patient" button visible
   - ✅ "Delete Patient" button visible (red)
3. Click "Edit Patient"
4. Verify:
   - ✅ Modal opens with form pre-filled with patient data
   - ✅ ICN field is read-only (grayed out)
5. Change address city to `Atlanta`
6. Click "Update Patient"
7. Verify:
   - ✅ Toast: "Patient updated: ..."
   - ✅ Modal closes
   - ✅ Page reloads showing updated city

---

#### V8: Delete Patient Confirmation

1. On patient detail page, click "Delete Patient"
2. Verify:
   - ✅ Browser confirmation dialog appears: "Are you sure you want to delete patient..."
3. Click "Cancel"
   - ✅ Dialog closes, no action taken
4. Click "Delete Patient" again, click "OK"
5. Verify:
   - ✅ Toast: "Patient deleted: ICN999001"
   - ✅ Redirects to dashboard
   - ✅ Patient no longer in roster

---

#### V9: ICN Auto-Generation

1. Create 3 patients in sequence
2. Check console logs or database:
```sql
SELECT icn FROM clinical.patient_demographics
WHERE icn LIKE 'ICN999%'
ORDER BY icn;
```
3. Verify:
   - ✅ ICNs are sequential: ICN999001, ICN999002, ICN999003
   - ✅ No gaps or duplicates

---

#### V10: Toast Auto-Dismiss

1. Create a patient
2. Observe toast notification
3. Verify:
   - ✅ Toast appears immediately after submission
   - ✅ Toast disappears after exactly 3 seconds
   - ✅ No manual close action needed

---

### Troubleshooting

**Issue: "Add New Patient" button doesn't open modal**
- Check browser console for JavaScript errors
- Verify HTMX is loaded in base.html
- Check Network tab - should see GET request to `/patient/create-form`

**Issue: Modal form doesn't close after successful creation**
- Check response from `/patient/create` endpoint
- Verify it includes `<script>closeModal();</script>`
- Check browser console for JavaScript errors

**Issue: Toast doesn't appear**
- Verify `<div id="toast-container"></div>` exists in template
- Check response includes `<div class="toast toast-success">...</div>`
- Inspect HTMX afterSwap event listener

**Issue: Table doesn't refresh after create/edit**
- Check hidden button `#roster-refresh-trigger` exists
- Verify it has correct `hx-get="/patient/roster-table"` attribute
- Check Network tab for refresh request

**Issue: ICN generation fails**
- Check PostgreSQL connection
- Verify query: `SELECT MAX(icn) FROM clinical.patient_demographics WHERE icn LIKE 'ICN999%'`
- Check service layer logs for exceptions

---

### Summary

Phase H.1 is now complete! You have implemented:

✅ **Service Layer** - patient_crud_service.py with create/update/delete/validate functions
✅ **Route Handlers** - patient_crud.py with 6 endpoints
✅ **Modal Forms** - Create and edit forms with full field coverage
✅ **Toast Notifications** - Custom 3-second auto-dismiss notifications
✅ **Dashboard Integration** - "Add New Patient" button with HTMX refresh
✅ **Patient Detail Integration** - Edit and delete buttons
✅ **Validation** - Client-side HTML5 + server-side Python
✅ **Auto-ICN Generation** - Sequential 999 series
✅ **CCOW Best Practices** - No unwanted context changes

**Files Created:**
- `app/services/patient_crud_service.py` (428 lines)
- `app/routes/patient_crud.py` (304 lines)
- `app/templates/partials/patient_roster_table.html`
- `app/templates/partials/patient_create_form.html` (243 lines)
- `app/templates/partials/patient_edit_form.html` (254 lines)

**Files Modified:**
- `app/main.py` (added router registration)
- `app/templates/dashboard.html` (added button, modal container, refresh trigger)
- `app/templates/patient_detail.html` (added edit/delete buttons)
- `app/templates/base.html` (added JavaScript functions)
- `app/static/css/style.css` (added ~200 lines of CSS)

**Next Phase:** After testing Phase H.1 thoroughly, proceed to **Section 10.6: Phase H.2 - Vitals CRUD**, which will follow the same pattern for clinical data CRUD operations.

---

**End of Phase H.1 Implementation Guide**
