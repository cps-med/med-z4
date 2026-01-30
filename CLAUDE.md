# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

med-z4 is a "Simple EHR" application that operates as a CCOW (Clinical Context Object Workgroup) participant and context manager in the med-z1 healthcare ecosystem. It simulates a primary Electronic Health Record system and validates multi-application patient context synchronization.

**Key Characteristics:**
- **Shares Database:** Connects to the existing med-z1 PostgreSQL database (`medz1`) and uses the same `auth` and `clinical` schemas
- **Database-Backed Authentication:** Full authentication with bcrypt password hashing, UUID session management, and audit logging
- **Bidirectional CCOW Integration:** Both receives and sets patient context through the CCOW Vault (port 8001)
- **Teal/Emerald Theme:** Visually distinct from med-z1's Blue/Slate theme
- **Port 8005:** Runs independently from med-z1 (port 8000)
- **Independent Sessions:** Uses separate session cookie (`med_z4_session_id`) to enable simultaneous logins to both applications
- **HTMX Polling:** Real-time context synchronization with 5-second polling interval

## Development Commands

### Running the Application
```bash
# Activate virtual environment
source .venv/bin/activate

# Run development server with hot reload
uvicorn app.main:app --reload --port 8005

# Access application
open http://localhost:8005
```

### Multi-Service Development Workflow
For full CCOW context synchronization, run all services (each in separate terminal):

```bash
# Terminal 1: med-z4 (this project)
cd ~/swdev/med/med-z4
source .venv/bin/activate
uvicorn app.main:app --port 8005 --reload

# Terminal 2: CCOW Vault (managed by med-z1)
cd ~/swdev/med/med-z1
source .venv/bin/activate
uvicorn ccow.main:app --port 8001 --reload

# Terminal 3: med-z1 (companion application)
cd ~/swdev/med/med-z1
source .venv/bin/activate
uvicorn app.main:app --port 8000 --reload
```

**Service URLs:**
- med-z4: http://localhost:8005
- med-z1: http://localhost:8000
- CCOW Vault: http://localhost:8001 (API docs at /docs)

### Environment Setup
```bash
# Create virtual environment
python3 -m venv .venv

# Install dependencies
pip install -r requirements.txt

# Verify configuration loads
python -c "from config import settings; print('Config OK')"
```

### Database Connection Test
The application requires connection to the shared `medz1` PostgreSQL database (managed by med-z1):
```python
# Quick database connectivity test (if database.py exists)
from database import engine
async with engine.connect() as conn:
    result = await conn.execute("SELECT 1")
    print("Database connected!")
```

### Useful Database Queries
```sql
-- List all patients
SELECT icn, name_display, dob, source_system
FROM clinical.patient_demographics
ORDER BY name_last, name_first;

-- List med-z4 created patients (999 series ICN)
SELECT icn, name_display, dob
FROM clinical.patient_demographics
WHERE icn LIKE 'ICN999%'
ORDER BY last_updated DESC;

-- Check active sessions
SELECT s.session_id, u.email, s.created_at, s.expires_at
FROM auth.sessions s
JOIN auth.users u ON s.user_id = u.user_id
WHERE s.is_active = TRUE;

-- View recent audit logs
SELECT event_type, email, event_timestamp, success
FROM auth.audit_logs
ORDER BY event_timestamp DESC
LIMIT 20;
```

## Architecture

### Configuration Management (Pydantic-based)

Configuration is managed via `config.py` using **Pydantic Settings**, which automatically loads from `.env` file with type validation:

```python
from config import settings

# Access nested settings
settings.app.name          # Application name
settings.app.port          # Port (8005)
settings.session.secret_key
settings.ccow.base_url     # CCOW Vault URL
settings.vista.base_url    # VistA RPC Broker URL
```

**Environment Variable Prefixes:**
- `APP_*` → `settings.app`
- `SESSION_*` → `settings.session`
- `CCOW_*` → `settings.ccow`
- `VISTA_*` → `settings.vista`
- `SAMPLE_*` → `settings.sample`

### Application Structure

**FastAPI Application (`app/main.py`):**
- Entry point that registers all routers
- Mounts static files at `/static`
- Configures Jinja2 templates from `app/templates`

**Router Pattern:**
- Routes are organized by feature area in `app/routes/`:
  - `auth.py` - Authentication (login, logout)
  - `dashboard.py` - Patient roster with full CCOW integration
  - `ccow.py` - CCOW context operations (placeholder, not currently used)
  - `admin.py` - Admin/test endpoints
  - `health.py` - Health checks for CCOW and VistA services
- Each router uses `APIRouter` with prefix and tags
- Routes import from service layer for business logic

**Service Layer:**
- Business logic separated from route handlers in `app/services/`
- `auth_service.py` - Authentication, session management, password verification (bcrypt)
- `ccow_service.py` - CCOW Vault v2.1 API integration with X-Session-ID header authentication
- Pattern: Routes call services, services return data or None on error

**Templates:**
- Base template: `app/templates/base.html`
- Partials for HTMX: `app/templates/partials/`
- Routes pass `request` object and data to templates

### Database Schema (Shared with med-z1)

The application **does not create its own database**. It connects to the existing `medz1` PostgreSQL database:

**Schemas Used:**
- `auth` schema: User authentication, sessions, audit logs, CCOW context tracking
- `clinical` schema: Patient demographics, vitals, allergies, medications, encounters, labs, clinical notes, immunizations (12 tables total)
- `reference` schema: Lookup tables (CVX vaccine codes)

**Auth Schema Tables (SQLAlchemy Models in `app/models/auth.py`):**
- `auth.users` - User accounts (UUID primary key, bcrypt password hash, account locking)
- `auth.sessions` - Active user sessions (UUID, expiration tracking, IP/user agent)
- `auth.audit_logs` - Authentication and clinical event audit trail

**Note:** No `auth.ccow_contexts` table is needed - the CCOW Vault maintains context in-memory, keyed by `user_id`.

**Key Fields:**
- User authentication uses email + bcrypt password hash
- Sessions expire after 25 minutes (configurable via `SESSION_TIMEOUT_MINUTES`)
- Failed login attempts tracked (account locks after 5 failures)
- CCOW contexts linked to sessions for multi-app patient context sharing

**Patient Identity:**
- All clinical tables keyed by `patient_key` (ICN - Integrated Care Number)
- ICN format: `"ICN100001"`, `"ICN100002"`, etc.
- New patients created by med-z4 use 999 series: `"ICN999001"`

### CCOW Context Synchronization (v2.1 API)

med-z4 acts as both a **context participant** (follows context changes) and **context manager** (sets context) using the CCOW Vault v2.1 API.

**v2.1 API Pattern (Implemented):**
- med-z4 passes its session UUID via `X-Session-ID` header to CCOW Vault
- CCOW Vault validates session against shared `auth.sessions` table
- Context is keyed by `user_id` (extracted from session), not session_id
- Same user logged into both med-z1 and med-z4 sees same patient context

**v2.1 API Endpoints:**
- `GET /ccow/active-patient` - Get current user's active patient
- `PUT /ccow/active-patient` - Set active patient (body: `{patient_id, set_by}`)
- `DELETE /ccow/active-patient` - Clear active patient context

**Bidirectional Context Flow:**

**Participant Mode (med-z1 → med-z4):**
1. User selects patient in med-z1 → calls `PUT /ccow/active-patient`
2. med-z4 polls CCOW Vault every 5 seconds (`GET /ccow/active-patient`)
3. Detects context change → highlights patient in roster
4. Shows banner: "ACTIVE PATIENT: [Patient Name] (ICN)"

**Manager Mode (med-z4 → med-z1):**
1. User clicks "View" button on patient in med-z4 roster
2. med-z4 calls `PUT /ccow/active-patient` with patient ICN via X-Session-ID header
3. CCOW Vault updates context for user
4. med-z1 polls and detects change → updates UI
5. med-z4 shows alert: "Context set to: [Patient Name]"

**Implementation Details:**
- Service layer: `app/services/ccow_service.py` (v2.1 methods: `get_active_patient`, `set_active_patient`, `clear_active_patient`)
- HTMX polling endpoint: `/context/banner` (returns HTML fragment every 5 seconds)
- Patient selection endpoint: `/patient/select/{icn}` (sets context, returns JSON)
- Context clear endpoint: `/context/clear` (clears active patient)
- CCOW banner partial: `app/templates/partials/ccow_banner.html`
- No local context tracking table - CCOW Vault maintains context per-user in-memory
- Logout: CCOW context is preserved (recommended approach)


### HTMX Integration

The application uses HTMX for dynamic UI updates without full page reloads:
- Polling pattern for context updates (5-second intervals)
- Partial template rendering for dynamic content
- Routes return HTML fragments for HTMX swap operations

## Implementation Phases

The design document (`docs/spec/med-z4-design.md`) defines implementation phases with detailed step-by-step guides:

### Completed Phases

**Phase A-D: Foundation** (Section 10.0)
- CSS theme (Teal/Emerald color scheme)
- Login page with mock authentication
- Dashboard with patient roster
- Database connectivity (asyncpg, SQLAlchemy async)

**Phase E: Real Authentication** (Section 10.1) ✅
- SQLAlchemy models: User, Session, AuditLog
- Authentication service with bcrypt password hashing
- Session validation and expiration handling
- Account locking after failed login attempts
- Audit logging for security events

**Phase F: CCOW Integration** (Section 10.2) ✅
- CCOW service with v2.1 API (`get_active_patient`, `set_active_patient`, `clear_active_patient`)
- X-Session-ID header authentication pattern
- Dashboard displays current CCOW context on load
- CCOW banner with active/inactive states (`partials/ccow_banner.html`)
- HTMX polling endpoint (`/context/banner`) with 5-second refresh
- Patient selection endpoint (`/patient/select/{icn}`) for setting context
- Context clear endpoint (`/context/clear`) with "Clear" button in banner
- Patient row highlighting (`.patient-selected` CSS class)
- Gray color palette and `.btn-outline` button variant
- Bidirectional context synchronization with med-z1 verified

**Phase G: Patient Detail Page** (Section 10.3) ✅
- Patient service layer (`app/services/patient_service.py`) with data-fetching functions
- Patient detail route (`/patient/{icn}`) with automatic CCOW context setting
- Patient detail template with collapsible sections using HTML `<details>` elements
- Three clinical data sections: Vitals, Allergies, Medications
- Professional table formatting with proper spacing
- Empty state handling for missing data
- Compact section headers and patient demographics display
- Consistent navigation header with logout button across all pages
- "← Back to Roster" navigation link
- Placeholder "+ Add" buttons (disabled) for Phase H CRUD operations

**Monitoring Dashboard** (`docs/spec/med-z4-monitoring-dashboard.md`) ✅
- Monitoring service layer (`app/services/monitoring_service.py`) with health check functions
- Monitoring routes (`app/routes/monitoring.py`) for system health and active monitoring
- Active Sessions monitor - Real-time view of logged-in users and session details
- Database Health Check - PostgreSQL connectivity and statistics
- med-z1 Health Check - Companion application availability
- CCOW Active Patients - System-wide patient context monitoring
- CCOW Context History - Audit trail of recent context changes
- Dashboard monitoring panel with two-tiered button layout
- HTML partials for monitoring tables (sessions, CCOW patients, CCOW history)
- CSS styling for monitoring panel, tables, and status messages

### In Progress

None - All planned phases through Phase G and the monitoring dashboard are complete.

### Planned Phases

**Phase H: Patient and Clinical CRUD**

Phase H is split into multiple sub-phases, each documented in separate specification files:

**Phase H.1: Patient Demographics CRUD** (`docs/spec/phase-h1-patient-demographics-crud.md`) - Ready for Implementation
- Create/edit/delete patient demographics from dashboard and detail page
- Modal dialog forms with full field coverage (26 fields)
- Client-side (HTML5) and server-side (Python) validation
- Custom toast notifications (3-second auto-dismiss)
- Auto-generated ICN assignment (999 series)
- HTMX-powered dynamic table refresh

**Phase H.2: Vitals CRUD** (Planned after H.1 completion)
- Create/edit/delete vital signs from patient detail page
- Following same modal/toast/validation patterns as H.1
- Will be documented in `docs/spec/phase-h2-vitals-crud.md`

**Phase H.3-H.5: Additional Clinical CRUD** (Planned after H.2)
- Allergies, Medications, Clinical Notes
- Following established patterns from H.1 and H.2

**Current Status:** Phases A-G complete and deployed. Monitoring dashboard implementation complete. Phase H.1 specification complete and ready for implementation.

## Authentication Patterns

**Session Validation Flow:**
```python
from app.services.auth_service import validate_session

# In route handler
session_id = request.cookies.get(settings.session.cookie_name)
user_info = await validate_session(db, session_id) if session_id else None

if not user_info:
    return RedirectResponse(url="/login", status_code=303)

# user_info contains: session_id, user_id, email, display_name, role
```

**Login Flow:**
```python
from app.services.auth_service import authenticate_user, create_session

# Authenticate against database
user = await authenticate_user(db, email, password)

if not user:
    # Show error - invalid credentials or account locked
    return templates.TemplateResponse("login.html", {"error": "..."})

# Create session
session_info = await create_session(db, user, ip_address, user_agent)

# Set cookie and redirect
response = RedirectResponse(url="/dashboard", status_code=303)
response.set_cookie(
    key=settings.session.cookie_name,
    value=session_info["session_id"],
    max_age=settings.session.cookie_max_age,
    httponly=True,
    samesite="lax"
)
```

**Template Context Pattern:**
All routes must pass `settings` to templates since `base.html` references it:
```python
return templates.TemplateResponse("template.html", {
    "request": request,
    "settings": settings,  # Required by base.html
    "user": user_info,     # Optional - shows logged-in user
    # ... other context
})
```

## Key Design Decisions

**Separate Session Cookies:**
- med-z4 uses `med_z4_session_id` (vs med-z1's `session_id`)
- Enables simultaneous login to both applications for testing
- Maintains independent session management

**Shared Database Pattern:**
- Simulates real enterprise healthcare IT (multiple apps, one data warehouse)
- Provides immediate consistency (no data sync needed)
- Trade-off: Schema coupling with med-z1

**Service Layer Abstraction:**
- External API calls isolated in service layer (not in routes)
- Makes route handlers testable and maintainable
- Authentication: `app/services/auth_service.py`
- CCOW integration: `app/services/ccow_service.py`

**UI/UX Patterns:**
- Sticky navigation header (CSS `position: sticky`)
- Logged-in user displayed in navigation header
- Selected patient highlighted in roster (`.patient-selected` CSS class)
- HTMX polling for real-time updates without page reload
- Alert confirmations for patient selection (will upgrade to modal/navigation in Phase G)

## Important Implementation Notes

**Database Schema Matching:**
- SQLAlchemy models must exactly match actual database schema
- Example: `auth.users` has `display_name`, `first_name`, `last_name` (not `name_display`, etc.)
- Use `\d auth.table_name` in psql to verify schema before modeling

**Cookie Alias Pattern:**
When reading session cookies in routes, the alias must match the settings:
```python
session_id: Optional[str] = Cookie(None, alias=settings.session.cookie_name)
```
NOT hardcoded like `alias="session_id"`

**Required Dependencies:**
- `asyncpg==0.31.0` - Async PostgreSQL driver
- `greenlet==3.3.1` - Required for SQLAlchemy async operations
- `bcrypt==4.2.1` - Password hashing
- `httpx==0.28.1` - Async HTTP client for CCOW calls

**Running Scripts as Modules:**
Scripts in subdirectories should be run as modules from project root:
```bash
python -m scripts.script_name
```
Requires `scripts/__init__.py` to exist.

**CCOW Vault Dependency:**
- med-z4 requires CCOW Vault to be running on port 8001
- Verify with: `curl http://localhost:8001/ccow/health`
- CCOW Vault is managed by the med-z1 project

**Testing CCOW v2.1 API with curl:**
```bash
# Health check
curl http://localhost:8001/ccow/health

# Get context (with X-Session-ID header)
curl -H "X-Session-ID: your-session-uuid" \
  http://localhost:8001/ccow/active-patient

# Set context
curl -X PUT \
  -H "X-Session-ID: your-session-uuid" \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"ICN100001","set_by":"med-z4"}' \
  http://localhost:8001/ccow/active-patient

# Clear context
curl -X DELETE \
  -H "X-Session-ID: your-session-uuid" \
  http://localhost:8001/ccow/active-patient
```

## Reference Documentation

- **Design Specification:** `docs/spec/med-z4-design.md` - Complete technical design with implementation roadmap (Phases A-H)
- **Monitoring Dashboard Specification:** `docs/spec/med-z4-monitoring-dashboard.md` - System health and monitoring dashboard implementation guide
- **Phase H.1 Implementation Guide:** `docs/spec/phase-h1-patient-demographics-crud.md` - Complete implementation guide for patient demographics CRUD operations with modal dialogs, toast notifications, and auto-generated ICN
- **Database Guide:** `docs/guide/med-z1-postgres-guide.md` - Comprehensive schema documentation for shared medz1 database with data source field values
- **README:** Basic project overview and database connection info
- **Section 10.1:** Phase E (Real Authentication) - Step-by-step authentication implementation
- **Section 10.2:** Phase F (CCOW Integration) - CCOW v2.1 bidirectional context guide
- **Section 10.3:** Phase G (Patient Detail Page) - Patient detail view implementation

## Troubleshooting

**CSS Not Loading:**
- Check static files are mounted: `app.mount("/static", ...)`
- Verify CSS files exist in `app/static/css/` directory
- Check browser Network tab for 404 errors

**HTMX Not Working:**
- Check HTMX script is included in `<head>` of base.html
- Open browser console for JavaScript errors
- Check Network tab - should see XHR requests
- Verify backend routes return HTML, not JSON

**Database Connection Failed:**
- Verify PostgreSQL is running: `docker ps`
- Check credentials in `.env` file
- Test connection: `psql -h localhost -U postgres -d medz1`

**Session Invalid After Login:**
- Check cookie is being set (browser dev tools > Application > Cookies)
- Verify SESSION_SECRET_KEY is at least 32 characters
- Check session in database: `SELECT * FROM auth.sessions ORDER BY created_at DESC LIMIT 1;`

**CCOW Context Not Syncing:**
- Verify CCOW vault is running on port 8001
- Check both apps are using same user (same user_id in vault)
- Verify session cookie/header is valid
- Check vault logs for errors

## Related Services

- **med-z1:** Longitudinal viewer (port 8000) - companion application
- **CCOW Context Vault:** Patient context service (port 8001) - managed by med-z1
- **VistA RPC Broker:** Real-time VistA data service (port 8003) - managed by med-z1
- **PostgreSQL:** Shared database (port 5432) - managed by med-z1
