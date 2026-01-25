# Med-Z4 (Simple EHR) Application Design

**Document Version:** v1.0  
**Date:** January 22, 2026  
**Repository:** `med-z4`  
**Status:** Ready for Implementation  
**Author:** Chuck Sylvester  

---

## Document Purpose

This design specification provides technical guidance for implementing med-z4, a standalone "Simple EHR" application that serves as a CCOW participant and clinical data management tool for the med-z1 ecosystem.

This document covers Phases 1-8 implementation (authentication, CCOW integration, patient roster, CRUD operations for clinical data). For more information on the implementation roadmap, refer to docs/spec/med-z4-roadmap.md.

---

## 1. Executive Summary

### 1.1 Purpose

med-z4 is a standalone "Simple EHR" application designed to simulate a primary Electronic Health Record system. Its role in the med-z1 ecosystem is to act as a CCOW Participant that validates multi-application patient context synchronization with the med-z1 longitudinal viewer.

Unlike med-z1 (which is a specialized read-only viewer), med-z4 simulates the "source of truth" workflow where a clinician actively manages patient data. It demonstrates that when a user changes patients in med-z4, the context automatically propagates to med-z1 via the central CCOW Context Vault, and vice versa.

### 1.2 Key Objectives

1. **Repository Isolation:** Operate as a completely self-sufficient application in the `med-z4` repository
2. **Shared Identity:** Connect to the existing med-z1 PostgreSQL database (`medz1`) to utilize the same `auth` and `clinical` schemas
3. **Context Interoperability:** Implement full CCOW operations (Get, Set, Clear) with proper authentication
4. **Production-Grade Authentication:** Bcrypt password hashing, secure session cookies, session expiration handling
5. **Clinical Data Management:** CRUD operations for patients, vitals, allergies, notes, and other clinical domains
6. **Visual Distinction:** Teal/Emerald theme to clearly differentiate from med-z1's Blue/Slate theme

### 1.3 Success Criteria

**Phase 1-5 (CCOW Context Synchronization):**
- User can log into both med-z1 and med-z4 with separate sessions
- Selecting a patient in med-z4 updates med-z1's active patient (and vice versa)
- Context changes are visible within 2-5 seconds (polling interval)
- Session validation prevents unauthorized access

**Phase 6-8 (Clinical Data Management):**
- User can create new patients with unique ICN identifiers (999 series)  
- User can add vitals, allergies, and clinical notes for any patient
- Data created in med-z4 immediately appears in med-z1 UI
- Data integrity constraints enforced (required fields, data types, foreign keys)

---

## 2. System Architecture

### 2.1 Ecosystem Overview

The med-z4 application operates alongside med-z1 as a peer CCOW participant, sharing database resources but maintaining strict application-level isolation.

```text
                       ┌──────────────────────────────────┐
                       │        Clinician (User)          │
                       └───────────────┬──────────────────┘
                                       │
                    ┌──────────────────┴───────────────────┐
                    │                                      │
            Browser Tab A                          Browser Tab B
          (localhost:8000)                       (localhost:8005)
                    │                                      │
      ┌─────────────▼──────────────┐         ┌─────────────▼──────────────┐
      │        med-z1 App          │         │        med-z4 App          │
      │   (Longitudinal Viewer)    │         │       (Simple EHR)         │
      │                            │         │                            │
      │  - Blue/Slate Theme        │         │  - Teal/Emerald Theme      │
      │  - Read-Only Clinical Data │         │  - CRUD Clinical Data      │
      │  - Dashboard Widgets       │         │  - Patient Roster          │
      │  - Port 8000               │         │  - Port 8005               │
      └─────────────┬──────────────┘         └─────────────┬──────────────┘
                    │                                      │
                    │     ┌─────────────────────────┐      │
                    └─────►   CCOW Context Vault    ◄──────┘
                          │     (Port 8001)         │
                          │                         │
                          │ Multi-User Context Mgmt │
                          │   Session Validation    │
                          └────────────┬────────────┘
                                       │
                                       │ SQL Queries
                                       │ (auth.sessions validation)
                                       │ (clinical data read/write)
                                       │
                  ┌────────────────────▼──────────────────────┐
                  │       PostgreSQL Database (medz1)         │
                  │                                           │
                  │   ┌───────────────────────────────────┐   │
                  │   │  Schema: auth                     │   │
                  │   │  - users (shared)                 │   │
                  │   │  - sessions (shared)              │   │
                  │   │  - audit_logs (shared)            │   │
                  │   └───────────────────────────────────┘   │
                  │                                           │
                  │  ┌────────────────────────────────────┐   │
                  │  │  Schema: clinical                  │   │
                  │  │  - patient_demographics            │   │
                  │  │  - patient_vitals                  │   │
                  │  │  - patient_allergies               │   │
                  │  │  - patient_clinical_notes          │   │
                  │  │  - patient_medications_*           │   │
                  │  │  - patient_encounters              │   │
                  │  │  - patient_labs                    │   │
                  │  │  - patient_immunizations           │   │
                  │  │  (12 clinical tables total)        │   │
                  │  └────────────────────────────────────┘   │
                  │                                           │
                  │  ┌────────────────────────────────────┐   │
                  │  │  Schema: reference                 │   │
                  │  │  - vaccine (CVX codes)             │   │
                  │  └────────────────────────────────────┘   │
                  └───────────────────────────────────────────┘
```

### 2.2 Integration Points

| Component | Configuration | Description |
|-----------|--------------|-------------|
| **Service Port** | 8005 | Distinct from med-z1 (8000), CCOW Vault (8001), VistA RPC Broker (8003) |
| **Database Host** | localhost:5432 | Shared PostgreSQL instance running in Docker |
| **Database Name** | medz1 | Same database as med-z1 (shared schemas) |
| **Database User** | postgres | Shared credential (from `.env` file) |
| **CCOW Vault URL** | http://localhost:8001 | Targets existing CCOW Context Vault service |
| **Session Cookie Name** | med_z4_session_id | Different from med-z1 to enable independent sessions |
| **Session Timeout** | 25 minutes | Matches med-z1 default (configurable) |
| **Cookie Security** | HttpOnly=True, SameSite=Lax | Production-ready security settings |

**Key Decision: Separate Session Cookies**  
med-z4 uses a different session cookie name (med_z4_session_id) than med-z1 (session_id) for the following reasons:

- **Independent Testing:** Allows user to log into both applications simultaneously with different user accounts
- **Session Isolation:** Prevents accidental session conflicts or overwrites
- **Production Realism:** Simulates real-world scenario where different EHR systems maintain separate sessions
- **Security:** Each application validates its own sessions independently

### 2.3 Technology Stack

med-z4 uses the exact same technology stack as med-z1 for consistency and learning transfer:

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Language** | Python | 3.11 (macOS) / 3.10 (Linux) | Application runtime |
| **Web Framework** | FastAPI | Latest | REST API and web application framework |
| **Template Engine** | Jinja2 | Latest | Server-side HTML rendering |
| **Interactivity** | HTMX | 1.9.x | Dynamic UI updates without JavaScript |
| **Session Management** | Starlette SessionMiddleware | Latest | Encrypted session cookies |
| **Database** | PostgreSQL | 16 | Shared with med-z1 |
| **ORM** | SQLAlchemy | 2.x | Database queries and models |
| **Password Hashing** | bcrypt | Latest | Secure password storage |
| **HTTP Client** | httpx | Latest | CCOW Vault communication |
| **ASGI Server** | Uvicorn | Latest | Development server with hot reload |

**Why This Stack?**

- **FastAPI:** Modern, fast, automatic API documentation, type hints, async support
- **Jinja2:** Mature templating with inheritance, macros, filters (Django-like syntax)
- **HTMX:** Server-side rendering with SPA-like UX (no complex JavaScript build tooling)
- **Starlette Sessions:** Built-in encrypted cookie sessions (no Redis/database needed for Phase 1)
- **SQLAlchemy:** Industry-standard Python ORM with raw SQL support when needed
- **bcrypt:** Industry-standard password hashing (slow by design to resist brute-force attacks)

---

### 2.3 Repository Structure

med-z4 follows a flat, simple structure, as shown below:

```text
med-z4/
├── .env                                # Environment configuration (DB credentials, secrets)
├── .gitignore                          # Git ignore patterns (Python, IDE, secrets)
├── README.md                           # Quick start guide and development instructions
├── requirements.txt                    # Python dependencies with pinned versions
├── config.py                           # Centralized configuration loader (reads .env)
├── database.py                         # SQLAlchemy database engine and session management
├── main.py                             # FastAPI application entry point
│
├── docs/                               # Application documentation
│   ├── guide/                          # Developer setup and other guides
│   └── spec/                           # Design specifications
│
└── app/                                # Application code (models, routes, services)
    ├── __init__.py
    │
    ├── models/                         # Database models (SQLAlchemy/Pydantic)
    │   ├── __init__.py
    │   ├── auth.py                     # User, Session models (matches med-z1 auth schema)
    │   └── clinical.py                 # Clinical models (Patient, Vital, Allergy, Note)
    │
    ├── routes/                         # FastAPI route handlers (endpoints)
    │   ├── __init__.py
    │   ├── auth.py                     # Login, logout, session management
    │   ├── dashboard.py                # Patient roster, dashboard
    │   ├── context.py                  # CCOW context operations (get/set/clear)
    │   └── crud.py                     # Patient/clinical data CRUD operations (Phase 6+)
    │
    ├── services/                       # Business logic layer
    │   ├── __init__.py
    │   ├── auth_service.py             # Password verification, session creation
    │   ├── ccow_client.py              # CCOW Vault HTTP client
    │   ├── patient_service.py          # Patient data operations (Phase 6+)
    │   └── audit_service.py            # Clinical audit logging
    │
    ├── templates/                      # Jinja2 HTML templates
    │   ├── base.html                   # Base layout with Teal theme
    │   ├── login.html                  # Login form with password input
    │   ├── dashboard.html              # Patient roster table
    │   ├── patient_form.html           # New/edit patient form (Phase 6+)
    │   ├── patient_detail.html         # Patient detail page with tabs (Phase 6+)
    │   │
    │   └── partials/                   # HTMX partial templates (fragments)
    │       ├── patient_row.html        # Single patient table row
    │       ├── ccow_banner.html        # Top banner with active patient
    │       ├── ccow_debug_panel.html   # CCOW status widget
    │       └── forms/                  # Reusable form components (Phase 6+)
    │           ├── vital_form.html
    │           ├── allergy_form.html
    │           └── note_form.html
    │
    ├── middleware/                     # Custom middleware (if needed)
    │   └── __init__.py
    │
    └── static/                             # Static assets (CSS, JS, images)
        ├── css/
        │   ├── style.css                   # Base styles and CSS variables
        │   ├── login.css                   # Login page styles
        │   ├── dashboard.css               # Dashboard/roster styles
        │   ├── patient_detail.css          # Patient detail page styles
        │   └── forms.css                   # Form styles
        ├── js/
        │   └── htmx.min.js                 # HTMX library (1.9.x)
        └── images/
            └── logo-teal.png               # med-z4 logo, favicon, and other images
```

**Directory Structure Rationale**

- **Flat Structure:** Easier to navigate for learning (vs. deeply nested packages)
- **models/:** Separates database models from business logic (Single Responsibility Principle)
- **routes/:** One file per major feature area (keeps route files manageable)
- **services/:** Business logic extracted from routes (testable, reusable)
- **templates/partials/:** HTMX pattern - small HTML fragments for dynamic updates
- **static/:** Public assets served directly by FastAPI StaticFiles middleware

With this structure, python module imports look like:
```python
from app.models.auth import User, Session
from app.services.auth_service import verify_password, create_session
from app.services.ccow_client import CCOWClient
```

---

## 3. Configuration Management

**3.1 Create and Clone Repository**

- Create `med-z4` GitHub repository
- Clone locally into `~/swdev/med` directory

**3.2 Create initial requirements.txt with pinned versions**  

```bash
# Initial set
fastapi==0.123.9
uvicorn==0.38.0
Jinja2==3.1.6
python-multipart==0.0.20
SQLAlchemy==2.0.36
psycopg2-binary==2.9.11
bcrypt==4.2.1
httpx==0.28.1
python-dotenv==1.2.1

# More to be added later...
```

**3.3 Create and prepare virtual environment**
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
pip list

# To deactivate virtual environment
deactivate
```

**3.4 Environment Variables (.env)**

The `.env` file stores all configuration and secrets. Never commit this file to Git.

**Template (.env example):**

```bash
# ---------------------------------------------------------------------
# med-z4 Configuration
# ---------------------------------------------------------------------

# Application Settings
APP_NAME=med-z4
APP_PORT=8005
DEBUG=True

# Session Management
SESSION_SECRET_KEY=your-secret-key-here-minimum-32-characters-long
SESSION_TIMEOUT_MINUTES=25
SESSION_COOKIE_NAME=med_z4_session_id

# PostgreSQL Database (Shared with med-z1)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=medz1
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-postgres-password-here

# CCOW Context Vault
CCOW_BASE_URL=http://localhost:8001

# Security Settings
BCRYPT_ROUNDS=12  # Password hashing cost factor (12 = ~300ms per hash)

# Logging
LOG_LEVEL=INFO
```

### 4.2 Configuration Loader (config.py)

Centralized configuration module (in project root folder) that loads and validates environment variables.

```python
# config.py
# Centralized configuration for med-z4
# Reads from .env file and provides typed config objects

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------
# Application Configuration
# ---------------------------------------------------------------------

APP_NAME = os.getenv("APP_NAME", "med-z4")
APP_PORT = int(os.getenv("APP_PORT", "8005"))
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

# ---------------------------------------------------------------------
# Session Configuration
# ---------------------------------------------------------------------

SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY")
if not SESSION_SECRET_KEY:
    raise ValueError("SESSION_SECRET_KEY must be set in .env file")
if len(SESSION_SECRET_KEY) < 32:
    raise ValueError("SESSION_SECRET_KEY must be at least 32 characters")

SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "25"))
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "med_z4_session_id")
SESSION_COOKIE_MAX_AGE = SESSION_TIMEOUT_MINUTES * 60  # Convert to seconds

# ---------------------------------------------------------------------
# Database Configuration
# ---------------------------------------------------------------------

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "medz1")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

if not POSTGRES_PASSWORD:
    raise ValueError("POSTGRES_PASSWORD must be set in .env file")

# SQLAlchemy async connection string
DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# ---------------------------------------------------------------------
# CCOW Configuration
# ---------------------------------------------------------------------

CCOW_BASE_URL = os.getenv("CCOW_BASE_URL", "http://localhost:8001")

# ---------------------------------------------------------------------
# Security Configuration
# ---------------------------------------------------------------------

BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))

# ---------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
```

**Configuration Pattern**

- **Fail Fast:** Raise errors on startup if required config is missing (don't fail later during runtime)
- **Type Conversion:** Convert strings to int/bool where needed (`int(os.getenv(...))`)
- **Sensible Defaults:** Provide defaults for non-sensitive settings (port, timeout)
- **Validation:** Check constraints (e.g., secret key length) before app starts
- **Single Import:** Other modules import from `config` (not `os.getenv` scattered everywhere)

---

## 5. Database Design & Schema Sharing

### 5.1 Shared Database Pattern

med-z4 **does not create its own database or schemas**. It operates as a client of the existing `medz1` PostgreSQL database created and managed by med-z1.

**Shared Schemas:**

| Schema | med-z4 Access | Purpose |
|--------|--------------|---------|
| `auth` | **Read/Write** | User authentication (login creates sessions) |
| `clinical` | **Read/Write** | Patient clinical data (roster display, CRUD operations) |
| `reference` | **Read-Only** | Reference data (CVX vaccine codes, etc.) |
| `public` | **No Access** | AI checkpoint tables (LangGraph, not used by med-z4) |

**Learning Note: Why Share a Database?**

This pattern simulates real enterprise healthcare IT:
- Multiple applications (CPRS, VistA, JLV, med-z1) query the same data warehouse
- No data duplication or synchronization complexity
- Immediate consistency (data written by med-z4 is instantly visible to med-z1)
- Testing realism (both apps see identical patient records)

**Trade-offs:**
- **Schema coupling:** If med-z1 changes table structure, med-z4 may break
- **Mitigation:** Use database views or abstraction layers (future enhancement)
- **For Phase 1-8:** Acceptable coupling for development/testing environment

### 5.2 Database Connection Management (database.py)

SQLAlchemy async engine and session factory for PostgreSQL connections:

```python
# database.py
# Database connection management for med-z4
# Uses SQLAlchemy 2.x async with connection pooling

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging

from config import DATABASE_URL, DEBUG

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Async Database Engine (Singleton)
# ---------------------------------------------------------------------

engine = create_async_engine(
    DATABASE_URL,
    echo=DEBUG,  # Log SQL queries if DEBUG=True
    pool_pre_ping=True,  # Verify connections before use
)

# Async session factory (creates new AsyncSession objects)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# ---------------------------------------------------------------------
# Session Dependency for FastAPI
# ---------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.

    Usage in routes:
        @app.get("/patients")
        async def list_patients(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Patient))
            patients = result.scalars().all()
            return patients

    The session is automatically closed after the request completes,
    even if an exception occurs.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# ---------------------------------------------------------------------
# Context Manager for Scripts (Optional)
# ---------------------------------------------------------------------

@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions in non-FastAPI code.

    Usage:
        async with get_db_context() as db:
            result = await db.execute(select(Patient).limit(1))
            patient = result.scalar_one_or_none()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

**Learning Note: SQLAlchemy Async Pattern**

- **Engine (Singleton):** Created once at module import, reused for all connections
- **AsyncSessionLocal (Factory):** Creates new AsyncSession objects for each request
- **get_db (Dependency):** FastAPI will call this for every request, automatically closing sessions
- **pool_pre_ping=True:** Checks connection health before use (handles database restarts)
- **echo=DEBUG:** Logs SQL queries to console when DEBUG=True (useful for learning)

### 5.3 Patient Identity: patient_key vs icn

**Current State:**
The PostgreSQL database uses both `patient_key` and `icn` columns in `clinical.patient_demographics`. Currently, these are **synonyms** (same value), but this may change in future if identity resolution becomes more complex.

**Canonical Rule for med-z4:**

> **Use `patient_key` as the canonical patient identifier in all database queries. Treat `icn` as a display/search field.**

**Why This Matters:**
- Future-proofs for identity resolution scenarios where 1 patient = multiple ICNs
- Matches med-z1 pattern (med-z1 uses `patient_key` internally)
- PostgreSQL foreign keys reference `patient_key`, not `icn`

**Implementation Guidance:**

| Use Case | Field to Use | Rationale |
|----------|-------------|-----------|
| Database queries (WHERE, JOIN) | `patient_key` | Primary key, canonical identifier |
| URL routes (`/patients/{...}`) | `icn` | User-facing, readable |
| CCOW context (`set_context`) | `icn` | CCOW standard uses ICN |
| Display in UI | `icn` | User recognizes ICN format |
| Foreign keys (vitals, allergies) | `patient_key` | Database integrity |

**Code Example:**

```python
@router.get("/patients/{icn}")
async def patient_detail(icn: str, db: AsyncSession = Depends(get_db)):
    # Convert icn (URL param) to patient_key (DB query)
    result = await db.execute(
        select(PatientDemographics).where(PatientDemographics.patient_key == icn)
    )
    patient = result.scalar_one_or_none()
```

**Current Simplification:**
For Phase 1-8, `patient_key == icn` (same value). The above pattern ensures code remains correct if identity resolution becomes more complex in future phases.

### 5.4 Database Access Model & Permissions

**Development Environment:**
- med-z4 connects using the `postgres` superuser (same as med-z1)
- **Justification:** Simplified development with shared `.env` configuration
- **Risk:** No permission boundaries in dev environment

**Production Environment (Recommended Pattern):**

Create a dedicated application-specific role with **minimum required privileges**:

```sql
-- Create dedicated med-z4 application role
CREATE ROLE med_z4_app WITH LOGIN PASSWORD '<secure-password>';

-- Grant schema usage
GRANT USAGE ON SCHEMA auth, clinical, reference TO med_z4_app;

-- Auth schema: SELECT (validate), INSERT (create sessions), UPDATE/DELETE (logout)
GRANT SELECT ON auth.users TO med_z4_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON auth.sessions TO med_z4_app;
GRANT INSERT ON auth.audit_logs TO med_z4_app;

-- Clinical schema: Full CRUD on patient-created data
GRANT SELECT, INSERT, UPDATE, DELETE ON clinical.patient_demographics TO med_z4_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON clinical.patient_vitals TO med_z4_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON clinical.patient_allergies TO med_z4_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON clinical.patient_clinical_notes TO med_z4_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON clinical.patient_immunizations TO med_z4_app;

-- Clinical schema: SELECT only on ETL-sourced tables
GRANT SELECT ON clinical.patient_encounters TO med_z4_app;
GRANT SELECT ON clinical.patient_medications_outpatient TO med_z4_app;
GRANT SELECT ON clinical.patient_labs TO med_z4_app;

-- Reference schema: SELECT only (read-only reference data)
GRANT SELECT ON ALL TABLES IN SCHEMA reference TO med_z4_app;

-- Grant sequence usage for auto-incrementing IDs
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA clinical TO med_z4_app;

-- Revoke public access (tighten security)
REVOKE ALL ON ALL TABLES IN SCHEMA clinical FROM PUBLIC;
```

**Permission Matrix:**

| Schema | Table/Group | med-z1 (read-only) | med-z4 (CRUD app) | Rationale |
|--------|-------------|-------------------|-------------------|-----------|
| `auth` | users | SELECT | SELECT | Both apps authenticate users |
| `auth` | sessions | SELECT, INSERT, DELETE | SELECT, INSERT, UPDATE, DELETE | Both apps manage their own sessions |
| `auth` | audit_logs | INSERT | INSERT | Both apps log auth events |
| `clinical` | patient_demographics | SELECT | **INSERT, UPDATE, DELETE** | med-z4 creates new patients |
| `clinical` | patient_vitals | SELECT | **INSERT, UPDATE, DELETE** | med-z4 records vitals |
| `clinical` | patient_allergies | SELECT | **INSERT, UPDATE, DELETE** | med-z4 manages allergies |
| `clinical` | clinical_notes | SELECT | **INSERT, UPDATE, DELETE** | med-z4 writes clinical notes |
| `clinical` | patient_encounters | SELECT | SELECT | ETL-sourced only (read-only for both) |
| `clinical` | patient_medications | SELECT | SELECT | ETL-sourced only (read-only for both) |
| `clinical` | patient_labs | SELECT | SELECT | ETL-sourced only (read-only for both) |
| `reference` | All tables | SELECT | SELECT | Reference data (read-only for all apps) |

---

## 6. Authentication Design

### 6.1 Authentication Philosophy

med-z4 implements **production-grade password authentication** with bcrypt hashing and secure session management. This differs from the draft "Mock SSO" dropdown approach to provide:

1. **Realistic EHR simulation:** Healthcare systems use password authentication
2. **Security learning:** Understanding proper password storage and session management
3. **Visual distinction:** Different login UI from med-z1 helps users distinguish applications
4. **Audit compliance:** Proper user authentication enables audit trails

### 6.2 Security Model

**Password Storage:**
- Passwords are **never stored in plaintext**
- Uses bcrypt hashing with salt (BCRYPT_ROUNDS=12, ~300ms per hash)
- Resistant to rainbow table and brute-force attacks
- Password hashes stored in `auth.users.password_hash` (shared with med-z1)

**Session Management:**
- Sessions stored in `auth.sessions` table (shared with med-z1)
- Session ID is a cryptographically secure UUID
- Session cookie is **HttpOnly** (prevents JavaScript access, XSS protection)
- Session cookie is **SameSite=Lax** (CSRF protection)
- Sessions expire after 25 minutes of inactivity (configurable)

**Session Isolation:**
- med-z4 uses **different cookie name** (`med_z4_session_id`) than med-z1 (`session_id`)
- Allows independent logins (user can be logged into both apps simultaneously)
- Each app validates its own sessions independently via CCOW vault

### 6.3 Database Models (app/models/auth.py)

```python
# app/models/auth.py
# Authentication models matching med-z1 auth schema

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase
import uuid

class Base(DeclarativeBase):
    pass

class User(Base):
    """
    User account model (auth.users table).
    med-z4 only READS from this table (doesn't create users).
    """
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    home_site_sta3n = Column(Integer)
    is_active = Column(Boolean, default=True)
    is_locked = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Session(Base):
    """
    Session model (auth.sessions table).
    med-z4 WRITES to this table when user logs in.
    """
    __tablename__ = "sessions"
    __table_args__ = {"schema": "auth"}

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.user_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    ip_address = Column(String(45))
    user_agent = Column(Text)

class AuditLog(Base):
    """
    Audit log model (auth.audit_logs table).
    med-z4 WRITES to this table for authentication and clinical events.
    """
    __tablename__ = "audit_logs"
    __table_args__ = {"schema": "auth"}

    audit_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.user_id", ondelete="SET NULL"))
    event_type = Column(String(50), nullable=False)
    event_timestamp = Column(DateTime, default=datetime.utcnow)
    email = Column(String(255))
    ip_address = Column(String(45))
    user_agent = Column(Text)
    success = Column(Boolean)
    failure_reason = Column(Text)
    session_id = Column(UUID(as_uuid=True))
    details = Column(Text)  # Additional context for clinical events
```

### 6.4 Authentication Service (app/services/auth_service.py)

```python
# app/services/auth_service.py
# Authentication business logic for med-z4

import bcrypt
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import logging

from app.models.auth import User, Session as SessionModel, AuditLog
from config import SESSION_TIMEOUT_MINUTES

logger = logging.getLogger(__name__)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            password_hash.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """
    Authenticate user by email and password.
    Returns User object if authentication succeeds, None otherwise.
    """
    # Query user by email
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"Login attempt for non-existent user: {email}")
        await _log_failed_login(db, email, "User not found")
        return None

    if user.is_locked:
        logger.warning(f"Login attempt for locked account: {email}")
        await _log_failed_login(db, email, "Account locked")
        return None

    if not user.is_active:
        logger.warning(f"Login attempt for inactive account: {email}")
        await _log_failed_login(db, email, "Account inactive")
        return None

    if not verify_password(password, user.password_hash):
        logger.warning(f"Failed login attempt for {email}: Invalid password")
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.is_locked = True
            logger.warning(f"Account locked after 5 failed attempts: {email}")
        await db.commit()
        await _log_failed_login(db, email, "Invalid password")
        return None

    # Authentication successful - reset failed attempts
    user.failed_login_attempts = 0
    user.last_login_at = datetime.utcnow()
    await db.commit()

    logger.info(f"Successful login: {email}")
    return user


async def create_session(
    db: AsyncSession,
    user: User,
    ip_address: str,
    user_agent: str
) -> Dict[str, Any]:
    """Create a new session for authenticated user."""
    session_id = uuid.uuid4()
    expires_at = datetime.utcnow() + timedelta(minutes=SESSION_TIMEOUT_MINUTES)

    session = SessionModel(
        session_id=session_id,
        user_id=user.user_id,
        created_at=datetime.utcnow(),
        last_activity_at=datetime.utcnow(),
        expires_at=expires_at,
        is_active=True,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    db.add(session)

    # Log successful login
    audit_log = AuditLog(
        user_id=user.user_id,
        event_type="login",
        event_timestamp=datetime.utcnow(),
        email=user.email,
        ip_address=ip_address,
        user_agent=user_agent,
        success=True,
        session_id=session_id,
    )
    db.add(audit_log)
    await db.commit()

    logger.info(f"Session created for {user.email}: {session_id}")

    return {
        "session_id": str(session_id),
        "user_id": str(user.user_id),
        "expires_at": expires_at,
    }


async def invalidate_session(db: AsyncSession, session_id: str) -> bool:
    """Invalidate (logout) a session."""
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        logger.warning(f"Invalid session ID format: {session_id}")
        return False

    result = await db.execute(
        update(SessionModel)
        .where(SessionModel.session_id == session_uuid)
        .values(is_active=False)
    )
    await db.commit()

    if result.rowcount > 0:
        logger.info(f"Session invalidated: {session_id}")
        return True
    return False


async def _log_failed_login(db: AsyncSession, email: str, reason: str):
    """Internal helper to log failed login attempts."""
    audit_log = AuditLog(
        user_id=None,
        event_type="login_failed",
        event_timestamp=datetime.utcnow(),
        email=email,
        success=False,
        failure_reason=reason,
    )
    db.add(audit_log)
    await db.commit()
```

### 6.5 Session Validation Middleware

```python
# app/middleware/auth.py
# Session validation middleware for protected routes

from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Dict, Any
import uuid
import logging

from database import get_db
from app.models.auth import Session as SessionModel, User
from config import SESSION_COOKIE_NAME

logger = logging.getLogger(__name__)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    FastAPI dependency to validate session and extract current user.

    Returns dict with user info, or redirects to /login if invalid.
    """
    session_id = request.cookies.get(SESSION_COOKIE_NAME)

    if not session_id:
        logger.warning("No session cookie found")
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"}
        )

    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"}
        )

    # Query session
    result = await db.execute(
        select(SessionModel).where(SessionModel.session_id == session_uuid)
    )
    session = result.scalar_one_or_none()

    if not session or not session.is_active:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"}
        )

    if session.expires_at < datetime.utcnow():
        logger.warning(f"Session expired: {session_id}")
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"}
        )

    # Get user
    result = await db.execute(
        select(User).where(User.user_id == session.user_id)
    )
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"}
        )

    return {
        "user_id": str(user.user_id),
        "email": user.email,
        "display_name": user.display_name,
        "session_id": session_id,
    }
```

### 6.6 Audit Logging: Clinical Data Access

To support HIPAA compliance, med-z4 logs clinical data access events using the `auth.audit_logs` table.

**Extended Event Types:**

```python
# Authentication events
'login'              # Successful login
'logout'             # Explicit logout
'login_failed'       # Failed login attempt

# Clinical access events
'patient_view'       # Viewed patient detail page
'patient_create'     # Created new patient
'patient_update'     # Edited patient demographics
'vital_create'       # Added vital signs
'allergy_create'     # Added allergy
'note_create'        # Created clinical note
'note_view'          # Viewed full clinical note (sensitive text)
'ccow_set'           # Set CCOW context
'ccow_clear'         # Cleared CCOW context
```

**Audit Service (app/services/audit_service.py):**

```python
# app/services/audit_service.py
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.auth import AuditLog


async def log_clinical_event(
    db: AsyncSession,
    user_id: str,
    event_type: str,
    patient_icn: str | None = None,
    resource_id: int | None = None,
    details: str | None = None
):
    """
    Log clinical data access event for HIPAA compliance.
    """
    detail_str = f"Patient: {patient_icn}" if patient_icn else ""
    if resource_id:
        detail_str += f", Resource: {resource_id}"
    if details:
        detail_str += f", {details}"

    audit_log = AuditLog(
        user_id=user_id,
        event_type=event_type,
        event_timestamp=datetime.utcnow(),
        details=detail_str if detail_str else None
    )
    db.add(audit_log)
    await db.commit()
```

---

## 7. CCOW Context Management

### 7.1 CCOW Overview

**CCOW (Clinical Context Object Workgroup)** is an HL7 standard for synchronizing clinical application context. In the med-z1 ecosystem, the CCOW Context Vault (port 8001) acts as the central "single source of truth" for which patient is currently active.

**Key Concepts:**

- **Context:** The currently active patient (identified by ICN)
- **Participant:** An application that can get/set context (med-z1, med-z4, future CPRS, etc.)
- **Vault:** Central service that stores and distributes context (med-z1/ccow service)
- **Multi-User:** v2.0 vault supports independent contexts per user (user_id scoped)

**med-z4's Role:**

- **Context Driver:** Sets patient context when user selects from roster
- **Context Listener:** Polls vault to detect when med-z1 (or other apps) change context
- **Authenticated Participant:** All CCOW operations require valid session cookie

### 7.2 CCOW Vault API Reference

The CCOW Context Vault exposes a REST API (v2.0) documented at http://localhost:8001/docs.

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/ccow/health` | Health check | No |
| GET | `/ccow/active-patient` | Get current user's active patient | Yes (session cookie) |
| PUT | `/ccow/active-patient` | Set current user's active patient | Yes (session cookie) |
| DELETE | `/ccow/active-patient` | Clear current user's active patient | Yes (session cookie) |
| GET | `/ccow/history?scope=user\|global` | Get context change history | Yes (session cookie) |
| GET | `/ccow/active-patients` | Get all users' contexts (admin) | Yes (session cookie) |

### 7.3 Session Cookie Contract with CCOW Vault

**Problem Statement:**
med-z4 uses a different session cookie name (`med_z4_session_id`) than med-z1 (`session_id`) to enable independent login sessions. The CCOW Vault must be able to validate sessions from both applications.

**CCOW Vault Implementation (v2.0):**

The CCOW Vault uses **cookie-name-agnostic session validation**:

1. **Vault reads ALL cookies** from incoming requests
2. **Searches for UUID-format values** in any cookie
3. **Validates each UUID** against `auth.sessions` table
4. **First valid session wins** (order: `session_id`, then `med_z4_session_id`, then other cookies)

**Contract Summary:**
- **Cookie Name:** Applications can use ANY cookie name (med-z4 uses `med_z4_session_id`)
- **Cookie Value:** Must be a valid UUID that exists in `auth.sessions` table
- **Vault Behavior:** Validates UUID value against database, ignores cookie name
- **Multi-User Support:** Different users in med-z1 and med-z4 can set context independently

### 7.4 CCOW Client (app/services/ccow_client.py)

```python
# app/services/ccow_client.py
# CCOW Context Vault client for med-z4

import httpx
from typing import Optional, Dict, Any
import logging

from config import CCOW_BASE_URL, SESSION_COOKIE_NAME

logger = logging.getLogger(__name__)


class CCOWClient:
    """
    Client for CCOW Context Vault API (v2.0).
    Automatically includes session cookie for authentication.
    """

    def __init__(self, session_id: str):
        self.base_url = CCOW_BASE_URL
        self.session_id = session_id
        self.cookies = {SESSION_COOKIE_NAME: session_id}

    async def get_context(self) -> Optional[Dict[str, Any]]:
        """Get current user's active patient context."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/ccow/active-patient",
                    cookies=self.cookies,
                    timeout=5.0,
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return None  # No context exists
                elif response.status_code == 401:
                    logger.warning("CCOW vault rejected session (401)")
                    return None
                else:
                    logger.error(f"CCOW get_context error: {response.status_code}")
                    return None

        except httpx.RequestError as e:
            logger.error(f"CCOW vault connection error: {e}")
            return None

    async def set_context(self, patient_id: str, set_by: str = "med-z4") -> bool:
        """Set current user's active patient context."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}/ccow/active-patient",
                    json={"patient_id": patient_id, "set_by": set_by},
                    cookies=self.cookies,
                    timeout=5.0,
                )

                if response.status_code == 200:
                    logger.info(f"CCOW context set: {patient_id} by {set_by}")
                    return True
                else:
                    logger.error(f"CCOW set_context error: {response.status_code}")
                    return False

        except httpx.RequestError as e:
            logger.error(f"CCOW vault connection error: {e}")
            return False

    async def clear_context(self, cleared_by: str = "med-z4") -> bool:
        """Clear current user's active patient context."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/ccow/active-patient",
                    json={"cleared_by": cleared_by},
                    cookies=self.cookies,
                    timeout=5.0,
                )

                if response.status_code in (204, 404):
                    logger.info("CCOW context cleared")
                    return True
                else:
                    logger.error(f"CCOW clear_context error: {response.status_code}")
                    return False

        except httpx.RequestError as e:
            logger.error(f"CCOW vault connection error: {e}")
            return False

    async def health_check(self) -> bool:
        """Check if CCOW vault is reachable."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/ccow/health",
                    timeout=5.0,
                )
                return response.status_code == 200
        except httpx.RequestError:
            return False
```

---

## 8. Core Features (Phase 1-5)

### 8.1 Feature: Patient Roster (Dashboard)

**Purpose:** Display list of all patients from `clinical.patient_demographics` with "Select" action.

**Route:** `GET /dashboard`

**UI Components:**
- Table with columns: Name, ICN, DOB, Sex, Age
- "Select" button for each patient (sets CCOW context)
- Active patient banner at top (shows current context)
- CCOW debug panel (optional, for development)

**Implementation:** See Section 10 (Phase 3) for complete route and template code.

### 8.2 Feature: Active Patient Banner

**Purpose:** Display currently active patient from CCOW context at top of page. Updates automatically via HTMX polling every 5 seconds.

**Route:** `GET /context/banner` (HTMX partial)

**Implementation:** See Section 11.3 (Dashboard Screen) for template and CSS.

### 8.3 Feature: CCOW Debug Panel

**Purpose:** Show CCOW vault status and context details for debugging during development. Displays vault health status (online/offline), current context patient ID, which application set the context, and last sync timestamp.

**Route:** `GET /context/debug` (HTMX partial)

**UI Components:**
- Fixed position panel in bottom-right corner
- Vault health indicator (green = online, red = offline)
- Current context patient ID
- "Set By" application name
- Last sync timestamp
- Auto-refreshes every 5 seconds via HTMX polling

**Implementation:** See Section 11.10 (Component Library) for complete template, CSS, and route handler code.

---

## 9. Clinical Data Management (CRUD) - Phase 6-8

### 9.1 CRUD Philosophy: "Sandcastle Strategy"

**Purpose:** med-z4 enables creation of synthetic patient data directly in the PostgreSQL serving database to support testing of med-z1 features.

**The "Sandcastle" Model:**

Data created via med-z4 is intentionally **ephemeral** ("sandcastles"):
- **Immediate feedback:** Data appears instantly in med-z1 UI (no ETL delay)
- **Testing focus:** Supports CCOW testing, UI validation, AI feature testing
- **Temporary:** Data is wiped when med-z1 ETL pipeline runs (rebuilds from CDWWork)
- **Clean slate:** Ensures test environment doesn't accumulate stale data over time

**This is a feature, not a bug.** med-z1 is designed to be rebuilt from source data regularly.

### 9.2 Test Data Identification: 999 Series ICN

To distinguish manually-created patients from ETL-sourced patients:

**ICN Generation Pattern:**
- **ETL patients:** `ICN100001` through `ICN100999` (from mock CDWWork)
- **med-z4 patients:** `999V######` (e.g., `999V123456`, `999V987654`)

**Benefits:**
- Easy visual identification (999 prefix signals "test data")
- No collision with ETL data
- Follows VA ICN format (V = "verified")

**ICN Generator (app/services/patient_service.py):**

```python
import random
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.clinical import PatientDemographics


async def generate_unique_icn(db: AsyncSession) -> str:
    """
    Generate unique 999-series ICN for med-z4 created patients.
    Format: 999V###### where ###### is random 6-digit number.
    """
    for attempt in range(10):
        suffix = random.randint(100000, 999999)
        candidate_icn = f"999V{suffix}"

        result = await db.execute(
            select(PatientDemographics.patient_key)
            .where(PatientDemographics.patient_key == candidate_icn)
        )
        if result.scalar_one_or_none() is None:
            return candidate_icn

    raise Exception("Failed to generate unique ICN after 10 attempts")
```

### 9.3 Data Ownership & ETL Interaction

**Source System Tagging:**

All clinical tables include a `source_system` column to identify data origin:

| Value | Description |
|-------|-------------|
| `'ETL'` | Data sourced from med-z1 ETL pipeline |
| `'med-z4'` | Data created directly by med-z4 application |
| `'VistA-RPC'` | Real-time data from VistA RPC Broker (T-0 layer) |

**ETL Refresh Behavior:**

1. ETL drops all rows with `source_system='ETL'` and reloads from Gold Parquet
2. Rows with `source_system='med-z4'` are **NOT deleted**
3. Result: med-z4-created data survives ETL refreshes

### 9.4 Clinical Data Models (app/models/clinical.py)

```python
# app/models/clinical.py
# Clinical data models matching med-z1 serving database schema

from datetime import datetime, date
from sqlalchemy import Column, String, Integer, Date, DateTime, Text, DECIMAL, Boolean, TIMESTAMP
from app.models.auth import Base


class PatientDemographics(Base):
    """Patient demographics model (clinical.patient_demographics)."""
    __tablename__ = "patient_demographics"
    __table_args__ = {"schema": "clinical"}

    patient_key = Column(String(50), primary_key=True)
    icn = Column(String(50), unique=True, nullable=False)
    ssn = Column(String(64))
    ssn_last4 = Column(String(4))
    name_last = Column(String(100))
    name_first = Column(String(100))
    name_display = Column(String(200))
    dob = Column(Date)
    age = Column(Integer)
    sex = Column(String(1))
    gender = Column(String(50))
    primary_station = Column(String(10))
    primary_station_name = Column(String(200))
    address_street1 = Column(String(100))
    address_city = Column(String(100))
    address_state = Column(String(2))
    address_zip = Column(String(10))
    phone_primary = Column(String(20))
    deceased_flag = Column(String(1))
    death_date = Column(Date)
    source_system = Column(String(20))
    last_updated = Column(TIMESTAMP, default=datetime.utcnow)


class PatientVital(Base):
    """Patient vital signs model (clinical.patient_vitals)."""
    __tablename__ = "patient_vitals"
    __table_args__ = {"schema": "clinical"}

    vital_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_key = Column(String(50), nullable=False)
    vital_sign_id = Column(Integer, unique=True, nullable=False)
    vital_type = Column(String(100), nullable=False)
    vital_abbr = Column(String(10), nullable=False)
    taken_datetime = Column(TIMESTAMP, nullable=False)
    entered_datetime = Column(TIMESTAMP)
    result_value = Column(String(50))
    numeric_value = Column(DECIMAL(10, 2))
    systolic = Column(Integer)
    diastolic = Column(Integer)
    unit_of_measure = Column(String(20))
    location_name = Column(String(100))
    entered_by = Column(String(100))
    abnormal_flag = Column(String(20))
    data_source = Column(String(20), default="med-z4")
    last_updated = Column(TIMESTAMP, default=datetime.utcnow)


class PatientAllergy(Base):
    """Patient allergy model (clinical.patient_allergies)."""
    __tablename__ = "patient_allergies"
    __table_args__ = {"schema": "clinical"}

    allergy_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_key = Column(String(50), nullable=False)
    allergy_sid = Column(Integer, unique=True, nullable=False)
    allergen_local = Column(String(255), nullable=False)
    allergen_standardized = Column(String(100), nullable=False)
    allergen_type = Column(String(50), nullable=False)
    severity = Column(String(50))
    severity_rank = Column(Integer)
    reactions = Column(Text)
    reaction_count = Column(Integer, default=0)
    origination_date = Column(TIMESTAMP, nullable=False)
    observed_date = Column(TIMESTAMP)
    historical_or_observed = Column(String(20))
    originating_site = Column(String(10))
    originating_site_name = Column(String(100))
    originating_staff = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_drug_allergy = Column(Boolean, default=False)
    last_updated = Column(TIMESTAMP, default=datetime.utcnow)


class ClinicalNote(Base):
    """Clinical note model (clinical.patient_clinical_notes)."""
    __tablename__ = "patient_clinical_notes"
    __table_args__ = {"schema": "clinical"}

    note_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_key = Column(String(50), nullable=False)
    tiu_document_sid = Column(Integer, unique=True, nullable=False)
    document_definition_sid = Column(Integer, nullable=False)
    document_title = Column(String(200), nullable=False)
    document_class = Column(String(50), nullable=False)
    vha_standard_title = Column(String(200))
    status = Column(String(50), nullable=False)
    reference_datetime = Column(TIMESTAMP, nullable=False)
    entry_datetime = Column(TIMESTAMP, nullable=False)
    author_name = Column(String(200))
    sta3n = Column(String(10))
    facility_name = Column(String(200))
    document_text = Column(Text)
    text_length = Column(Integer)
    text_preview = Column(String(500))
    source_system = Column(String(50), default="med-z4")
    last_updated = Column(TIMESTAMP, default=datetime.utcnow)
```

---

## 10. Implementation Roadmap

This section provides a phase-by-phase implementation guide with direct references to UI/UX specifications (Section 11) and complete code examples.

### 10.1 Routes and Templates Contract

Complete reference for all HTTP endpoints:

#### Authentication Routes

| Route | Method | Auth | Template/Response | HTMX |
|-------|--------|------|-------------------|------|
| `/login` | GET | No | `login.html` (full page) | No |
| `/login` | POST | No | Redirect to `/dashboard` or error | No |
| `/logout` | POST | Yes | Redirect to `/login` | No |

#### Dashboard & Patient Roster Routes

| Route | Method | Auth | Template/Response | HTMX |
|-------|--------|------|-------------------|------|
| `/dashboard` | GET | Yes | `dashboard.html` (full page) | Polls `/context/banner` |
| `/patients` | GET | Yes | Same as `/dashboard` | Same |

#### CCOW Context Routes (HTMX Partials)

| Route | Method | Auth | Template/Response | HTMX |
|-------|--------|------|-------------------|------|
| `/context/banner` | GET | Yes | `partials/ccow_banner.html` | Polled every 5s |
| `/context/set/{icn}` | POST | Yes | JSON `{"success": true}` | Triggers banner refresh |
| `/context/clear` | DELETE | Yes | JSON `{"success": true}` | Triggers banner refresh |
| `/context/debug` | GET | Yes | `partials/ccow_debug_panel.html` | Polled every 5s |

#### Patient CRUD Routes

| Route | Method | Auth | Template/Response | HTMX |
|-------|--------|------|-------------------|------|
| `/patients/new` | GET | Yes | `patient_form.html` | No |
| `/patients/new` | POST | Yes | Redirect to `/patients/{icn}` | Optional validation |
| `/patients/{icn}` | GET | Yes | `patient_detail.html` | Polls banner |
| `/patients/{icn}/vitals/new` | GET | Yes | `vital_form.html` | No |
| `/patients/{icn}/vitals/new` | POST | Yes | Redirect to `/patients/{icn}` | No |
| `/patients/{icn}/allergies/new` | POST | Yes | Redirect to `/patients/{icn}` | No |
| `/patients/{icn}/notes/new` | POST | Yes | Redirect to `/patients/{icn}` | No |

#### Health Check Routes

| Route | Method | Auth | Response |
|-------|--------|------|----------|
| `/health` | GET | No | JSON `{"status": "healthy"}` |
| `/` | GET | No | Redirect to `/dashboard` or `/login` |

---

### Phase 1: Foundation & Environment (Days 1-2)

**Goal:** Set up repository, dependencies, database connectivity

**Tasks:**

1. **Initialize Repository**
   ```bash
   mkdir med-z4 && cd med-z4
   git init
   touch .gitignore README.md requirements.txt
   ```

2. **Create requirements.txt**
   ```
   fastapi==0.109.0
   uvicorn[standard]==0.27.0
   jinja2==3.1.3
   python-multipart==0.0.6
   sqlalchemy[asyncio]==2.0.25
   asyncpg==0.29.0
   bcrypt==4.1.2
   httpx==0.26.0
   python-dotenv==1.0.1
   ```

3. **Create .env from template** (see Section 4.1)

4. **Create config.py** (see Section 4.2)

5. **Create database.py** (see Section 5.2)

6. **Test database connection:**
   ```python
   # test_db.py
   import asyncio
   from database import get_db_context
   
   async def test():
       async with get_db_context() as db:
           result = await db.execute("SELECT 1")
           print("Database connected!")
   
   asyncio.run(test())
   ```

**Verification:**
- `python test_db.py` succeeds
- Virtual environment activated

---

### Phase 2: Authentication (Days 2-3)

**Goal:** Implement password authentication and session management

**UI Reference:** Section 11.2 (Login Screen), Section 11.8 (Base Template)

**Tasks:**

1. **Create models** (`app/models/auth.py`) - see Section 6.3

2. **Create auth service** (`app/services/auth_service.py`) - see Section 6.4

3. **Create auth middleware** (`app/middleware/auth.py`) - see Section 6.5

4. **Create directory structure:**
   ```bash
   mkdir -p templates/partials static/css static/js static/images
   ```

5. **Create templates:**
   - `templates/base.html` - see Section 11.8
   - `templates/login.html` - see Section 11.2

6. **Create CSS files:**
   - `static/css/style.css` - see Section 11.1 (CSS variables)
   - `static/css/login.css` - see Section 11.2

7. **Create auth routes** (`app/routes/auth.py`):

```python
# app/routes/auth.py
from fastapi import APIRouter, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from app.services.auth_service import authenticate_user, create_session, invalidate_session
from config import SESSION_COOKIE_NAME, SESSION_COOKIE_MAX_AGE

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent", "unknown")

    user = await authenticate_user(db, email, password)

    if not user:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid email or password.",
        }, status_code=status.HTTP_401_UNAUTHORIZED)

    session_info = await create_session(db, user, ip_address, user_agent)

    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_info["session_id"],
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,  # Set True in production
    )
    return response


@router.post("/logout")
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id:
        await invalidate_session(db, session_id)

    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    return response
```

8. **Create main.py:**

```python
# main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routes import auth, dashboard, context, crud
from config import APP_NAME, DEBUG

app = FastAPI(title=APP_NAME, debug=DEBUG)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(context.router, prefix="/context")
app.include_router(crud.router, prefix="/patients")


@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard")


@app.get("/health")
async def health():
    return {"status": "healthy", "app": APP_NAME}
```

**Verification:**
- Visit http://localhost:8005/login
- Log in with test credentials (clinician.alpha@va.gov / VaDemo2025!)
- Redirects to /dashboard (will show error until Phase 3)
- Check database: `SELECT * FROM auth.sessions WHERE is_active = TRUE`

---

### Phase 3: CCOW Integration (Days 3-4)

**Goal:** Implement CCOW context operations with HTMX polling

**UI Reference:** Section 11.3 (Dashboard Screen), Section 11.7 (HTMX Patterns)

**Tasks:**

1. **Create CCOW client** (`app/services/ccow_client.py`) - see Section 7.4

2. **Create context routes** (`app/routes/context.py`):

```python
# app/routes/context.py
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Dict

from app.middleware.auth import get_current_user
from app.services.ccow_client import CCOWClient

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.post("/set/{patient_icn}")
async def set_context(patient_icn: str, user: Dict = Depends(get_current_user)):
    ccow = CCOWClient(session_id=user["session_id"])
    success = await ccow.set_context(patient_icn, set_by="med-z4")

    if not success:
        raise HTTPException(status_code=500, detail="CCOW vault error")

    return JSONResponse({"success": True, "patient_id": patient_icn})


@router.delete("/clear")
async def clear_context(user: Dict = Depends(get_current_user)):
    ccow = CCOWClient(session_id=user["session_id"])
    success = await ccow.clear_context(cleared_by="med-z4")

    if not success:
        raise HTTPException(status_code=500, detail="CCOW vault error")

    return JSONResponse({"success": True})


@router.get("/banner", response_class=HTMLResponse)
async def get_banner(request: Request, user: Dict = Depends(get_current_user)):
    ccow = CCOWClient(session_id=user["session_id"])
    context = await ccow.get_context()

    return templates.TemplateResponse("partials/ccow_banner.html", {
        "request": request,
        "context": context,
        "user": user,
    })
```

3. **Create dashboard route** (`app/routes/dashboard.py`):

```python
# app/routes/dashboard.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict

from database import get_db
from app.middleware.auth import get_current_user
from app.models.clinical import PatientDemographics
from app.services.ccow_client import CCOWClient

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get all patients
    result = await db.execute(
        select(PatientDemographics).order_by(
            PatientDemographics.name_last,
            PatientDemographics.name_first
        )
    )
    patients = result.scalars().all()

    # Get CCOW context
    ccow = CCOWClient(session_id=user["session_id"])
    context = await ccow.get_context()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "patients": patients,
        "context": context,
    })
```

4. **Create templates:**
   - `templates/dashboard.html` - see Section 11.3
   - `templates/partials/ccow_banner.html` - see Section 11.3
   - `static/css/dashboard.css` - see Section 11.3

5. **Download HTMX:**
   ```bash
   curl -o static/js/htmx.min.js https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js
   ```

**Verification:**
- Visit http://localhost:8005/dashboard
- Patient roster displays with Teal theme
- Click "Select" on a patient
- Banner updates to show active patient
- Open med-z1 - patient should sync within 5 seconds
- Select patient in med-z1 - med-z4 banner updates

---

### Phase 4-5: Polish & Testing (Days 4-5)

**Goal:** Refine UI, add debug panel, test CCOW synchronization

**Tasks:**

1. Add CCOW debug panel (optional)
2. Add search/filter to patient roster (optional)
3. Test multi-user scenarios
4. Document any issues

---

### Phase 6: Patient CRUD (Days 5-7)

**Goal:** Create new patients with unique 999-series ICN

**UI Reference:** Section 11.5 (Patient Form)

**Tasks:**

1. **Create clinical models** (`app/models/clinical.py`) - see Section 9.4

2. **Create patient service** (`app/services/patient_service.py`) - see Section 9.2

3. **Create CRUD routes** (`app/routes/crud.py`):

```python
# app/routes/crud.py
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, date
from typing import Dict
import random

from database import get_db
from app.middleware.auth import get_current_user
from app.models.clinical import PatientDemographics, PatientVital, PatientAllergy, ClinicalNote
from app.services.patient_service import generate_unique_icn
from app.services.audit_service import log_clinical_event

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/new", response_class=HTMLResponse)
async def new_patient_form(request: Request, user: Dict = Depends(get_current_user)):
    return templates.TemplateResponse("patient_form.html", {
        "request": request,
        "user": user,
        "patient": None,
        "today": date.today(),
    })


@router.post("/new")
async def create_patient(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    date_of_birth: date = Form(...),
    gender: str = Form(...),
    ssn: str | None = Form(None),
    user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Generate unique ICN
    icn = await generate_unique_icn(db)

    # Calculate age
    today = date.today()
    age = today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )

    # Create patient
    patient = PatientDemographics(
        patient_key=icn,
        icn=icn,
        name_first=first_name,
        name_last=last_name,
        name_display=f"{last_name.upper()}, {first_name}",
        dob=date_of_birth,
        age=age,
        sex=gender[0].upper() if gender else None,
        gender=gender,
        ssn=ssn,
        ssn_last4=ssn[-4:] if ssn and len(ssn) >= 4 else None,
        source_system="med-z4",
        last_updated=datetime.utcnow(),
    )

    db.add(patient)
    await db.commit()

    # Audit log
    await log_clinical_event(db, user["user_id"], "patient_create", icn)

    return RedirectResponse(url=f"/patients/{icn}", status_code=303)


@router.get("/{icn}", response_class=HTMLResponse)
async def patient_detail(
    icn: str,
    request: Request,
    user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get patient
    result = await db.execute(
        select(PatientDemographics).where(PatientDemographics.patient_key == icn)
    )
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Get vitals
    result = await db.execute(
        select(PatientVital)
        .where(PatientVital.patient_key == icn)
        .order_by(PatientVital.taken_datetime.desc())
        .limit(10)
    )
    vitals = result.scalars().all()

    # Get allergies
    result = await db.execute(
        select(PatientAllergy)
        .where(PatientAllergy.patient_key == icn)
    )
    allergies = result.scalars().all()

    # Get notes
    result = await db.execute(
        select(ClinicalNote)
        .where(ClinicalNote.patient_key == icn)
        .order_by(ClinicalNote.reference_datetime.desc())
        .limit(10)
    )
    notes = result.scalars().all()

    # Audit log
    await log_clinical_event(db, user["user_id"], "patient_view", icn)

    return templates.TemplateResponse("patient_detail.html", {
        "request": request,
        "user": user,
        "patient": patient,
        "vitals": vitals,
        "allergies": allergies,
        "notes": notes,
    })
```

4. **Create templates:**
   - `templates/patient_form.html` - see Section 11.5
   - `templates/patient_detail.html` - see Section 11.4
   - `static/css/forms.css` - see Section 11.5
   - `static/css/patient_detail.css` - see Section 11.4

**Verification:**
- Visit http://localhost:8005/patients/new
- Fill out form, submit
- Patient created with 999V###### ICN
- Patient appears in roster
- Patient visible in med-z1

---

### Phase 7: Clinical Data CRUD (Days 7-9)

**Goal:** Add vitals, allergies, and clinical notes for patients

**UI Reference:** Section 11.6 (Vital Signs Form)

**Tasks:**

1. Add vital creation route to `app/routes/crud.py`
2. Add allergy creation route
3. Add note creation route
4. Create form templates in `templates/partials/forms/`

**Verification:**
- Add vital to patient - appears in med-z1 Vitals widget
- Add allergy - appears in med-z1 allergy list
- Add note - appears in med-z1 Notes page

---

### Phase 8: Integration Testing (Days 9-10)

**Goal:** Full system testing and documentation

**Tasks:**

1. Run through all manual test cases (Section 12.1)
2. Test multi-user CCOW scenarios
3. Verify data appears correctly in med-z1
4. Update README with final instructions
5. Document any known issues

**Deliverables:**
- Fully functional med-z4 application (Phases 1-8)
- Comprehensive documentation
- Ready for deployment to shared development environment

---

## 11. UI/UX Design & Wireframes

### 11.1 Design Philosophy & CSS Variables

**Visual Identity:**
- **Primary Color:** Teal (#14b8a6) - clearly distinct from med-z1's Blue (#3b82f6)
- **Theme:** Professional healthcare application with clean, accessible design
- **Typography:** System font stack for optimal readability

**CSS Variables (static/css/style.css):**

```css
:root {
    /* Primary Colors (Teal/Emerald) */
    --primary-teal: #14b8a6;
    --primary-teal-light: #5eead4;
    --primary-teal-dark: #0d9488;
    --primary-50: #f0fdfa;
    --primary-100: #ccfbf1;
    --primary-500: #14b8a6;
    --primary-600: #0d9488;
    --primary-700: #0f766e;

    /* Semantic Colors */
    --success-green: #10b981;
    --warning-amber: #f59e0b;
    --danger-red: #ef4444;
    --info-blue: #3b82f6;

    /* Neutral Colors */
    --gray-50: #f9fafb;
    --gray-100: #f3f4f6;
    --gray-200: #e5e7eb;
    --gray-500: #6b7280;
    --gray-700: #374151;
    --gray-900: #111827;

    /* Typography */
    --text-xs: 0.75rem;
    --text-sm: 0.875rem;
    --text-base: 1rem;
    --text-lg: 1.125rem;
    --text-xl: 1.25rem;
    --text-2xl: 1.5rem;
    --text-3xl: 1.875rem;

    /* Spacing */
    --space-1: 0.25rem;
    --space-2: 0.5rem;
    --space-3: 0.75rem;
    --space-4: 1rem;
    --space-6: 1.5rem;
    --space-8: 2rem;
    --space-12: 3rem;
}

/* Reset */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
    font-size: var(--text-base);
    line-height: 1.6;
    color: var(--gray-700);
    background-color: var(--gray-50);
    min-height: 100vh;
}

/* Button Base */
.btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-2);
    padding: var(--space-3) var(--space-6);
    border: none;
    border-radius: 6px;
    font-size: var(--text-base);
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
}

.btn-primary {
    background-color: var(--primary-teal);
    color: white;
}

.btn-primary:hover {
    background-color: var(--primary-teal-dark);
    transform: translateY(-1px);
}

.btn-sm {
    padding: var(--space-2) var(--space-4);
    font-size: var(--text-sm);
}

.btn-danger {
    background-color: var(--danger-red);
    color: white;
}

/* Form Controls */
.form-group {
    margin-bottom: var(--space-6);
}

.form-group label {
    display: block;
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--gray-700);
    margin-bottom: var(--space-2);
}

.form-input {
    width: 100%;
    height: 44px;
    padding: var(--space-3) var(--space-4);
    border: 2px solid var(--gray-200);
    border-radius: 6px;
    font-size: var(--text-base);
    transition: all 0.2s ease;
}

.form-input:focus {
    outline: none;
    border-color: var(--primary-teal);
    box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.1);
}

/* Alerts */
.alert {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-4);
    border-radius: 6px;
    margin-bottom: var(--space-6);
    font-size: var(--text-sm);
}

.alert-error {
    background-color: #fee2e2;
    color: #991b1b;
    border-left: 4px solid var(--danger-red);
}

.alert-success {
    background-color: #d1fae5;
    color: #065f46;
    border-left: 4px solid var(--success-green);
}
```

### 11.2 Login Screen

**Wireframe:**
```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                    ┌─────────────────┐                      │
│                    │   [MED-Z4 LOGO] │                      │
│                    │  Simple EHR App │                      │
│                    └─────────────────┘                      │
│                                                             │
│              ╔═══════════════════════════════╗              │
│              ║         USER LOGIN            ║              │
│              ╠═══════════════════════════════╣              │
│              ║  Email:                       ║              │
│              ║  [____________________]       ║              │
│              ║                               ║              │
│              ║  Password:                    ║              │
│              ║  [____________________]       ║              │
│              ║                               ║              │
│              ║       [  Login  ]             ║              │
│              ╚═══════════════════════════════╝              │
│                                                             │
│              ┌───────────────────────────────┐              │
│              │ ℹ️  Test Credentials:         │              │
│              │    Email: clinician.alpha@... │              │
│              │    Password: VaDemo2025!      │              │
│              └───────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

**Template (templates/login.html):**

```html
{% extends "base.html" %}

{% block title %}Login - med-z4 Simple EHR{% endblock %}

{% block content %}
<div class="login-container">
  <div class="login-card">
    <div class="login-header">
      <h1>med-z4</h1>
      <p class="subtitle">Simple EHR Application</p>
    </div>

    {% if error %}
    <div class="alert alert-error">
      <strong>Login Failed:</strong> {{ error }}
    </div>
    {% endif %}

    <form method="POST" action="/login" class="login-form">
      <div class="form-group">
        <label for="email">Email Address</label>
        <input type="email" id="email" name="email" class="form-input"
               required autofocus placeholder="clinician.alpha@va.gov">
      </div>

      <div class="form-group">
        <label for="password">Password</label>
        <input type="password" id="password" name="password" class="form-input"
               required placeholder="Enter your password">
      </div>

      <button type="submit" class="btn btn-primary btn-block">
        Sign In to med-z4
      </button>
    </form>

    <div class="info-panel">
      <p><strong>Test Credentials:</strong></p>
      <p>Email: <code>clinician.alpha@va.gov</code></p>
      <p>Password: <code>VaDemo2025!</code></p>
    </div>
  </div>
</div>
{% endblock %}
```

**CSS (static/css/login.css):**

```css
.login-container {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #5eead4 0%, #14b8a6 50%, #0f766e 100%);
    padding: var(--space-4);
}

.login-card {
    background: white;
    border-radius: 8px;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
    width: 100%;
    max-width: 400px;
    padding: var(--space-8);
}

.login-header {
    text-align: center;
    margin-bottom: var(--space-8);
}

.login-header h1 {
    font-size: var(--text-3xl);
    color: var(--primary-teal);
    margin-bottom: var(--space-2);
}

.login-header .subtitle {
    color: var(--gray-500);
}

.btn-block {
    width: 100%;
    height: 48px;
}

.info-panel {
    margin-top: var(--space-6);
    padding: var(--space-4);
    background-color: #e0f2fe;
    border-left: 4px solid var(--info-blue);
    border-radius: 6px;
    font-size: var(--text-sm);
}

.info-panel code {
    background-color: white;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: monospace;
}
```

### 11.3 Dashboard / Patient Roster Screen

**Wireframe:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ med-z4 Simple EHR                    [CCOW: No Active Patient] [Logout] │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ╔═══════════════════════════════════════════════════════════════════════╗   │
│ ║  Patient Roster                                   [+ Add New Patient] ║   │
│ ╠═══════════════════════════════════════════════════════════════════════╣   │
│ ║  ┌─────────┬─────────────┬──────────┬───────────┬──────────────────┐  ║   │
│ ║  │ ICN     │ Name        │ Sex      │ DOB       │ Actions          │  ║   │
│ ║  ├─────────┼─────────────┼──────────┼───────────┼──────────────────┤  ║   │
│ ║  │ 999V... │ DOE, John   │ M        │ 1975-03-15│ [View] [Select]  │  ║   │
│ ║  │ 999V... │ SMITH, Jane │ F        │ 1982-07-22│ [View] [Select]  │  ║   │
│ ║  └─────────┴─────────────┴──────────┴───────────┴──────────────────┘  ║   │
│ ║                                                                       ║   │
│ ║  Total Patients: 2                                                    ║   │
│ ╚═══════════════════════════════════════════════════════════════════════╝   │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Template (templates/dashboard.html):**

```html
{% extends "base.html" %}

{% block title %}Patient Roster - med-z4{% endblock %}

{% block content %}
<!-- CCOW Banner (polled every 5 seconds) -->
<div id="ccow-banner"
     hx-get="/context/banner"
     hx-trigger="load, every 5s"
     hx-swap="outerHTML">
    {% include "partials/ccow_banner.html" %}
</div>

<!-- Patient Roster -->
<div class="dashboard-container">
    <div class="dashboard-header">
        <h1>Patient Roster</h1>
        <a href="/patients/new" class="btn btn-primary">+ Add New Patient</a>
    </div>

    <table class="patient-table">
        <thead>
            <tr>
                <th>ICN</th>
                <th>Name</th>
                <th>Sex</th>
                <th>DOB</th>
                <th>Age</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for patient in patients %}
            <tr class="{% if context and context.patient_id == patient.icn %}active-context{% endif %}">
                <td><code>{{ patient.icn }}</code></td>
                <td>{{ patient.name_display }}</td>
                <td>{{ patient.sex or 'N/A' }}</td>
                <td>{{ patient.dob.strftime('%Y-%m-%d') if patient.dob else 'N/A' }}</td>
                <td>{{ patient.age or 'N/A' }}</td>
                <td>
                    <a href="/patients/{{ patient.icn }}" class="btn btn-sm">View</a>
                    <button class="btn btn-sm btn-primary"
                            hx-post="/context/set/{{ patient.icn }}"
                            hx-swap="none"
                            hx-on::after-request="htmx.trigger('#ccow-banner', 'load')">
                        Select
                    </button>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <p class="roster-count">Total Patients: {{ patients|length }}</p>
</div>
{% endblock %}
```

**CCOW Banner Partial (templates/partials/ccow_banner.html):**

```html
<div id="ccow-banner" class="ccow-banner {% if context %}active{% else %}inactive{% endif %}">
    {% if context and context.patient_id %}
    <div class="banner-content">
        <span class="banner-label">ACTIVE PATIENT:</span>
        <strong>{{ context.patient_id }}</strong>
        <span class="banner-source">(Set by {{ context.set_by }})</span>
        <button class="btn btn-sm btn-danger"
                hx-delete="/context/clear"
                hx-swap="none"
                hx-on::after-request="htmx.trigger('#ccow-banner', 'load')">
            Clear
        </button>
    </div>
    {% else %}
    <div class="banner-content empty">
        <span>No Active Patient - Select from roster below</span>
    </div>
    {% endif %}
</div>
```

### 11.4 Patient Detail Screen

**Wireframe:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ [Header: med-z4 | CCOW Banner | Logout]                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ← Back to Roster                                                           │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ PATIENT: DOE, John                         ICN: 999V123456            │  │
│  │ DOB: 1975-03-15 (49 years)  |  Sex: Male  |  [Set as CCOW Context]    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ▼ Vital Signs (3)                                      [+ Add Vital]       │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 2025-01-20  BP: 120/80 mmHg  |  HR: 72 bpm  |  Temp: 98.6°F          │  │
│  │ 2025-01-15  BP: 118/78 mmHg  |  HR: 70 bpm  |  Temp: 98.4°F          │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ▼ Allergies (2)                                        [+ Add Allergy]     │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ PENICILLIN (Drug) - Severity: SEVERE - Reaction: Hives               │  │
│  │ SHELLFISH (Food) - Severity: MODERATE - Reaction: Nausea             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ▼ Clinical Notes (1)                                   [+ Add Note]        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 2025-01-20 | Progress Note | Dr. Smith | "Patient presents with..."  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 11.5 Add/Edit Patient Form

See full template in Phase 6 implementation guide above.

### 11.6 Add Vital Signs Form

Similar structure to patient form with fields for:
- Date/Time of measurement
- Blood Pressure (systolic/diastolic)
- Heart Rate (bpm)
- Temperature (°F)
- Respiratory Rate (breaths/min)
- Oxygen Saturation (%)

### 11.7 HTMX Patterns (Summary)


### 11.8 Complete CSS Files

The following sections contain the complete CSS files for production use.

### 11.8.1 Dashboard CSS (static/css/dashboard.css)

```css
/* static/css/dashboard.css */

/* Dashboard Container */
.dashboard-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--space-6);
}

/* Card Component */
.card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: var(--space-6);
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-6);
  border-bottom: 2px solid var(--gray-200);
}

.card-title {
  font-size: var(--text-xl);
  font-weight: bold;
  color: var(--gray-900);
  margin: 0;
}

.card-body {
  padding: var(--space-6);
}

/* CCOW Banner */
.ccow-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-6);
  border-radius: 8px;
  margin-bottom: var(--space-6);
  transition: all 0.3s ease;
}

.ccow-banner.active {
  background: linear-gradient(90deg, #d1fae5 0%, #a7f3d0 100%);
  border-left: 4px solid var(--primary-teal);
}

.ccow-banner.inactive {
  background: var(--gray-100);
  border-left: 4px solid var(--gray-400);
}

.ccow-indicator {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.ccow-icon {
  width: 24px;
  height: 24px;
}

.ccow-banner.active .ccow-icon {
  color: var(--primary-teal);
}

.ccow-banner.inactive .ccow-icon {
  color: var(--gray-400);
}

.ccow-label {
  font-weight: 600;
  font-size: var(--text-base);
  color: var(--gray-900);
}

.ccow-patient-info {
  display: flex;
  gap: var(--space-6);
  align-items: center;
  flex: 1;
  margin: 0 var(--space-6);
}

.patient-name {
  font-weight: bold;
  font-size: var(--text-lg);
  color: var(--gray-900);
}

.patient-icn,
.patient-dob {
  font-size: var(--text-sm);
  color: var(--gray-700);
}

.ccow-hint {
  font-size: var(--text-sm);
  color: var(--gray-600);
  margin: 0;
  margin-left: auto;
}

/* Data Table */
.table-container {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table thead {
  background-color: var(--primary-teal);
  color: white;
}

.data-table th {
  padding: var(--space-4);
  text-align: left;
  font-weight: 600;
  font-size: var(--text-sm);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.data-table tbody tr {
  border-bottom: 1px solid var(--gray-200);
  transition: background-color 0.2s ease;
}

.data-table tbody tr:nth-child(even) {
  background-color: var(--gray-50);
}

.data-table tbody tr:hover {
  background-color: #ccfbf1;
}

.data-table tbody tr.active-context {
  background-color: #d1fae5;
  border-left: 3px solid var(--primary-teal);
}

.data-table td {
  padding: var(--space-4);
  font-size: var(--text-sm);
  color: var(--gray-700);
}

.actions-cell {
  display: flex;
  gap: var(--space-2);
}

.table-footer {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--gray-200);
}

.roster-count {
  font-size: var(--text-sm);
  color: var(--gray-600);
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: var(--space-12) var(--space-6);
}

.empty-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto var(--space-4);
  color: var(--gray-300);
}

.empty-message {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--gray-700);
  margin-bottom: var(--space-2);
}

.empty-hint {
  font-size: var(--text-sm);
  color: var(--gray-500);
  font-style: italic;
}

/* Badges */
.badge {
  display: inline-block;
  padding: var(--space-1) var(--space-3);
  border-radius: 12px;
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
}

.badge-neutral {
  background-color: var(--gray-200);
  color: var(--gray-700);
}

.badge-teal {
  background-color: var(--primary-100);
  color: var(--primary-700);
}

/* Button Variants */
.btn-outline {
  background: transparent;
  border: 2px solid var(--primary-teal);
  color: var(--primary-teal);
}

.btn-outline:hover {
  background: var(--primary-teal);
  color: white;
}

.btn-ghost {
  background: transparent;
  color: var(--gray-700);
}

.btn-ghost:hover {
  background: var(--gray-100);
}

.btn-icon-sm {
  width: 16px;
  height: 16px;
}

/* Utility Classes */
.font-mono {
  font-family: 'Courier New', monospace;
}

.font-semibold {
  font-weight: 600;
}

.text-sm {
  font-size: var(--text-sm);
}

.text-gray-600 {
  color: var(--gray-600);
}
```

### 11.8.2 Patient Detail CSS (static/css/patient_detail.css)

```css
/* static/css/patient_detail.css */

/* Patient Detail Container */
.patient-detail-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-6);
}

/* Back Link */
.back-link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--primary-teal);
  text-decoration: none;
  font-size: var(--text-sm);
  font-weight: 500;
  margin-bottom: var(--space-4);
}

.back-link:hover {
  text-decoration: underline;
}

.back-link svg {
  width: 16px;
  height: 16px;
}

/* Detail List */
.detail-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--space-6);
  margin: 0;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.detail-item dt {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--gray-600);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.detail-item dd {
  font-size: var(--text-lg);
  color: var(--gray-900);
  margin: 0;
}

.patient-name {
  font-weight: bold;
  font-size: var(--text-xl);
  color: var(--primary-teal-dark);
}

.age-badge {
  font-size: var(--text-sm);
  color: var(--gray-600);
  font-weight: normal;
}

/* Clinical Section */
.clinical-section {
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  margin-bottom: var(--space-4);
  overflow: hidden;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4);
  background-color: var(--gray-50);
  border-bottom: 1px solid var(--gray-200);
}

.section-toggle {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  font-size: var(--text-base);
}

.section-icon {
  width: 20px;
  height: 20px;
  color: var(--gray-600);
  transition: transform 0.2s ease;
}

.section-icon.rotate-90 {
  transform: rotate(90deg);
}

.section-title {
  font-weight: 600;
  color: var(--gray-900);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 24px;
  padding: 0 var(--space-2);
  background-color: var(--primary-teal);
  color: white;
  border-radius: 12px;
  font-size: var(--text-xs);
  font-weight: bold;
}

.section-content {
  padding: var(--space-4);
}

/* Vitals List */
.vitals-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.vital-item {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3);
  background-color: var(--gray-50);
  border-radius: 6px;
  border-left: 3px solid var(--primary-teal);
  transition: opacity 1s ease-out;
}

.vital-item.htmx-swapping {
  opacity: 0;
}

.vital-date {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--gray-700);
  min-width: 140px;
}

.vital-reading {
  font-size: var(--text-sm);
  color: var(--gray-900);
  padding: var(--space-1) var(--space-3);
  background-color: white;
  border-radius: 4px;
}

.vital-reading.abnormal {
  background-color: #fee2e2;
  color: var(--danger-red);
  font-weight: 600;
}

.vital-actions {
  margin-left: auto;
  display: flex;
  gap: var(--space-2);
}

/* Allergies List */
.allergies-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.allergy-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  background-color: var(--gray-50);
  border-radius: 6px;
  border-left: 3px solid var(--warning-amber);
  transition: opacity 1s ease-out;
}

.allergy-item.htmx-swapping {
  opacity: 0;
}

.allergy-item.severe {
  border-left-color: var(--danger-red);
  background-color: #fef2f2;
}

.allergy-info {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex: 1;
}

.allergen-name {
  font-size: var(--text-base);
  font-weight: bold;
  color: var(--gray-900);
}

.severity-badge {
  padding: var(--space-1) var(--space-3);
  border-radius: 12px;
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
}

.severity-severe {
  background-color: var(--danger-red);
  color: white;
}

.severity-moderate {
  background-color: var(--warning-amber);
  color: white;
}

.severity-mild {
  background-color: #fbbf24;
  color: var(--gray-900);
}

.reaction-text {
  font-size: var(--text-sm);
  color: var(--gray-600);
}

.allergy-actions {
  display: flex;
  gap: var(--space-2);
}

/* Notes List */
.notes-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.note-item {
  padding: var(--space-4);
  background-color: var(--gray-50);
  border-radius: 6px;
  border-left: 3px solid var(--info-blue);
  transition: opacity 1s ease-out;
}

.note-item.htmx-swapping {
  opacity: 0;
}

.note-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
  font-size: var(--text-sm);
}

.note-date {
  font-weight: 600;
  color: var(--gray-700);
}

.note-type {
  padding: var(--space-1) var(--space-2);
  background-color: var(--info-blue);
  color: white;
  border-radius: 4px;
  font-size: var(--text-xs);
  font-weight: 600;
}

.note-author {
  color: var(--gray-600);
}

.note-preview {
  font-size: var(--text-sm);
  color: var(--gray-700);
  margin-bottom: var(--space-3);
  line-height: 1.6;
}

.note-actions {
  display: flex;
  gap: var(--space-2);
}

/* Button Variants */
.btn-xs {
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-xs);
  height: auto;
}

/* Action Buttons Group */
.action-buttons {
  display: flex;
  gap: var(--space-2);
}

/* Page Footer */
.page-footer {
  margin-top: var(--space-8);
  padding-top: var(--space-6);
  border-top: 1px solid var(--gray-200);
}
```

### 11.8.3 Forms CSS (static/css/forms.css)

```css
/* static/css/forms.css */

/* Form Container */
.form-container {
  max-width: 800px;
  margin: 0 auto;
  padding: var(--space-6);
}

/* Form Section */
.form-section {
  border: none;
  padding: 0;
  margin: 0 0 var(--space-8) 0;
}

.section-legend {
  font-size: var(--text-lg);
  font-weight: bold;
  color: var(--gray-900);
  margin-bottom: var(--space-6);
  padding-bottom: var(--space-3);
  border-bottom: 2px solid var(--gray-200);
}

/* Form Grid */
.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--space-6);
}

.form-group.full-width {
  grid-column: 1 / -1;
}

/* Form Group */
.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.form-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--gray-700);
}

.form-label.required::after {
  content: "*";
  color: var(--danger-red);
  font-weight: bold;
  margin-left: var(--space-1);
}

.optional-badge {
  display: inline-block;
  padding: 2px var(--space-2);
  background-color: var(--gray-200);
  color: var(--gray-600);
  font-size: var(--text-xs);
  font-weight: normal;
  border-radius: 4px;
  text-transform: uppercase;
}

/* Form Input */
.form-input {
  width: 100%;
  height: 44px;
  padding: var(--space-3) var(--space-4);
  border: 2px solid var(--gray-200);
  border-radius: 6px;
  font-size: var(--text-base);
  color: var(--gray-900);
  background-color: white;
  transition: all 0.2s ease;
}

.form-input:focus {
  outline: none;
  border-color: var(--primary-teal);
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.1);
}

.form-input::placeholder {
  color: var(--gray-400);
}

.form-input:disabled {
  background-color: var(--gray-100);
  color: var(--gray-500);
  cursor: not-allowed;
}

/* Textarea */
textarea.form-input {
  height: auto;
  min-height: 120px;
  resize: vertical;
}

/* Select */
select.form-input {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3E%3Cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='m6 8 4 4 4-4'/%3E%3C/svg%3E");
  background-position: right 12px center;
  background-repeat: no-repeat;
  background-size: 16px;
  padding-right: 40px;
}

/* Input States */
.form-input.error {
  border-color: var(--danger-red);
}

.form-input.success {
  border-color: var(--success-green);
}

/* Radio Group */
.radio-group {
  display: flex;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.radio-option {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: var(--space-3) var(--space-4);
  border: 2px solid var(--gray-200);
  border-radius: 6px;
  transition: all 0.2s ease;
  min-width: 120px;
}

.radio-option:hover {
  border-color: var(--primary-teal-light);
  background-color: #f0fdfa;
}

.radio-option input[type="radio"] {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.radio-option input[type="radio"]:checked + .radio-label {
  color: var(--primary-teal-dark);
}

.radio-option:has(input:checked) {
  border-color: var(--primary-teal);
  background-color: #ccfbf1;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-base);
  font-weight: 500;
  color: var(--gray-700);
}

.radio-icon {
  width: 20px;
  height: 20px;
}

/* Field Help Text */
.field-help {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--gray-500);
  font-style: italic;
}

.help-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  color: var(--info-blue);
}

/* Field Error */
.field-error {
  display: none;
  font-size: var(--text-xs);
  color: var(--danger-red);
  font-weight: 500;
}

.field-error:not(:empty) {
  display: block;
}

/* Error Summary */
.error-summary {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-4);
  background-color: #fee2e2;
  border-left: 4px solid var(--danger-red);
  border-radius: 6px;
  margin-bottom: var(--space-6);
}

.error-summary:empty {
  display: none;
}

.error-summary .alert-icon {
  width: 24px;
  height: 24px;
  color: var(--danger-red);
  flex-shrink: 0;
}

.error-title {
  font-weight: 600;
  color: #991b1b;
  margin-bottom: var(--space-2);
}

.error-list {
  list-style: disc;
  padding-left: var(--space-4);
  margin: 0;
  font-size: var(--text-sm);
  color: #991b1b;
}

/* Form Actions */
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-4);
  margin-top: var(--space-8);
  padding-top: var(--space-6);
  border-top: 1px solid var(--gray-200);
}

/* Patient Context in Header */
.patient-context {
  font-size: var(--text-base);
  font-weight: normal;
  color: var(--gray-600);
  margin-left: var(--space-3);
}

.patient-context::before {
  content: "—";
  margin-right: var(--space-2);
  color: var(--gray-400);
}

/* DateTime Group */
.datetime-group {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: var(--space-3);
}

/* Blood Pressure Group */
.bp-group {
  display: flex;
  align-items: flex-end;
  gap: var(--space-3);
}

.bp-input-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.bp-label {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--gray-600);
}

.bp-input {
  width: 100px;
}

.bp-separator {
  font-size: var(--text-2xl);
  font-weight: bold;
  color: var(--gray-400);
  padding-bottom: var(--space-2);
}

/* Input with Unit */
.input-with-unit {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.unit-label {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--gray-600);
  white-space: nowrap;
}

/* Number Input Stepper Styling */
input[type="number"] {
  -moz-appearance: textfield;
}

input[type="number"]::-webkit-inner-spin-button,
input[type="number"]::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

/* Loading State */
.btn.loading {
  position: relative;
  color: transparent;
  pointer-events: none;
}

.btn.loading::after {
  content: "";
  position: absolute;
  width: 20px;
  height: 20px;
  top: 50%;
  left: 50%;
  margin-left: -10px;
  margin-top: -10px;
  border: 2px solid transparent;
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
```

### 11.9 Complete Templates

#### 11.9.1 Base Template (templates/base.html)

```html
{# templates/base.html #}
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}med-z4 Simple EHR{% endblock %}</title>

  {# CSS - Order matters: base styles first #}
  <link rel="stylesheet" href="/static/css/style.css">
  <link rel="stylesheet" href="/static/css/login.css">
  <link rel="stylesheet" href="/static/css/dashboard.css">
  <link rel="stylesheet" href="/static/css/patient_detail.css">
  <link rel="stylesheet" href="/static/css/forms.css">

  {# HTMX #}
  <script src="/static/js/htmx.min.js"></script>

  {# Alpine.js (for collapsible sections) #}
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>

  {% block extra_head %}{% endblock %}
</head>
<body>
  {# Header Navigation (only on authenticated pages) #}
  {% if user %}
  <header class="app-header">
    <div class="header-container">
      <div class="header-left">
        <a href="/dashboard" class="logo-link">
          <svg class="logo-icon" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
          </svg>
          <span class="logo-text">med-z4</span>
          <span class="logo-subtitle">Simple EHR</span>
        </a>
      </div>

      <div class="header-center">
        {# CCOW Status Badge in Header #}
        <div
          id="header-ccow-status"
          hx-get="/context/status-badge"
          hx-trigger="load, every 5s"
          hx-swap="innerHTML"
        >
          <span class="ccow-badge ccow-inactive">No Active Context</span>
        </div>
      </div>

      <div class="header-right">
        <span class="user-info">
          <svg class="user-icon" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"/>
          </svg>
          {{ user.display_name }}
        </span>
        <form action="/logout" method="POST" style="display: inline;">
          <button type="submit" class="btn btn-sm btn-ghost">
            <svg class="btn-icon-sm" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M3 3a1 1 0 00-1 1v12a1 1 0 102 0V4a1 1 0 00-1-1zm10.293 9.293a1 1 0 001.414 1.414l3-3a1 1 0 000-1.414l-3-3a1 1 0 10-1.414 1.414L14.586 9H7a1 1 0 100 2h7.586l-1.293 1.293z"/>
            </svg>
            Logout
          </button>
        </form>
      </div>
    </div>
  </header>
  {% endif %}

  {# Main Content #}
  <main class="main-content">
    {% block content %}{% endblock %}
  </main>

  {# Footer #}
  <footer class="app-footer">
    <p>&copy; 2026 med-z4 Simple EHR | CCOW Testing Application</p>
  </footer>

  {% block extra_scripts %}{% endblock %}
</body>
</html>
```

#### 11.9.2 Patient Form Template (templates/patient_form.html)

```html
{# templates/patient_form.html #}
{% extends "base.html" %}

{% block title %}
  {% if patient %}Edit Patient{% else %}Add New Patient{% endif %} - med-z4
{% endblock %}

{% block content %}
<div class="form-container">
  <a href="{% if patient %}/patients/{{ patient.icn }}{% else %}/dashboard{% endif %}" class="back-link">
    <svg viewBox="0 0 20 20" fill="currentColor">
      <path fill-rule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z"/>
    </svg>
    {% if patient %}Back to Patient{% else %}Back to Roster{% endif %}
  </a>

  <div class="card">
    <div class="card-header">
      <h2 class="card-title">
        {% if patient %}Edit Patient{% else %}Add New Patient{% endif %}
      </h2>
    </div>

    <div class="card-body">
      <form
        method="POST"
        action="{% if patient %}/patients/{{ patient.icn }}/edit{% else %}/patients/new{% endif %}"
        class="patient-form"
      >
        {# Error Summary #}
        <div id="form-errors">
          {% if errors %}
          {% include "partials/form_errors.html" %}
          {% endif %}
        </div>

        {# Personal Information Section #}
        <fieldset class="form-section">
          <legend class="section-legend">Personal Information</legend>

          <div class="form-grid">
            {# First Name #}
            <div class="form-group">
              <label for="first_name" class="form-label required">First Name</label>
              <input
                type="text"
                id="first_name"
                name="first_name"
                class="form-input"
                value="{{ patient.name_first if patient else '' }}"
                required
                maxlength="50"
                autofocus
                placeholder="Enter first name"
              >
              <span class="field-error" id="first_name-error"></span>
            </div>

            {# Last Name #}
            <div class="form-group">
              <label for="last_name" class="form-label required">Last Name</label>
              <input
                type="text"
                id="last_name"
                name="last_name"
                class="form-input"
                value="{{ patient.name_last if patient else '' }}"
                required
                maxlength="50"
                placeholder="Enter last name"
              >
              <span class="field-error" id="last_name-error"></span>
            </div>

            {# Date of Birth #}
            <div class="form-group">
              <label for="date_of_birth" class="form-label required">Date of Birth</label>
              <input
                type="date"
                id="date_of_birth"
                name="date_of_birth"
                class="form-input"
                value="{{ patient.dob.strftime('%Y-%m-%d') if patient and patient.dob else '' }}"
                required
                max="{{ today.strftime('%Y-%m-%d') }}"
              >
              <span class="field-help">Patient must be born before today</span>
              <span class="field-error" id="date_of_birth-error"></span>
            </div>

            {# Gender #}
            <div class="form-group">
              <label class="form-label required">Gender</label>
              <div class="radio-group">
                <label class="radio-option">
                  <input type="radio" name="gender" value="M"
                    {% if patient and patient.sex == 'M' %}checked{% endif %} required>
                  <span class="radio-label">
                    <svg class="radio-icon" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"/>
                    </svg>
                    Male
                  </span>
                </label>

                <label class="radio-option">
                  <input type="radio" name="gender" value="F"
                    {% if patient and patient.sex == 'F' %}checked{% endif %} required>
                  <span class="radio-label">
                    <svg class="radio-icon" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"/>
                    </svg>
                    Female
                  </span>
                </label>

                <label class="radio-option">
                  <input type="radio" name="gender" value="O"
                    {% if patient and patient.sex == 'O' %}checked{% endif %} required>
                  <span class="radio-label">
                    <svg class="radio-icon" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"/>
                    </svg>
                    Other
                  </span>
                </label>
              </div>
              <span class="field-error" id="gender-error"></span>
            </div>

            {# SSN (Optional) #}
            <div class="form-group">
              <label for="ssn" class="form-label">
                Social Security Number
                <span class="optional-badge">Optional</span>
              </label>
              <input
                type="text"
                id="ssn"
                name="ssn"
                class="form-input"
                value="{{ patient.ssn if patient and patient.ssn else '' }}"
                pattern="[0-9]{9}"
                maxlength="9"
                placeholder="123456789"
              >
              <span class="field-help">
                <svg class="help-icon" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"/>
                </svg>
                9 digits, no dashes. Will be masked in display (***-**-1234).
              </span>
              <span class="field-error" id="ssn-error"></span>
            </div>
          </div>
        </fieldset>

        {# Form Actions #}
        <div class="form-actions">
          <a href="{% if patient %}/patients/{{ patient.icn }}{% else %}/dashboard{% endif %}" class="btn btn-outline">
            Cancel
          </a>
          <button type="submit" class="btn btn-primary">
            {% if patient %}Save Changes{% else %}Create Patient{% endif %}
          </button>
        </div>
      </form>
    </div>
  </div>
</div>
{% endblock %}
```

#### 11.9.3 Patient Detail Template (templates/patient_detail.html)

```html
{# templates/patient_detail.html #}
{% extends "base.html" %}

{% block title %}{{ patient.name_display }} - med-z4{% endblock %}

{% block content %}
<div class="patient-detail-container">
  {# Back Link #}
  <a href="/dashboard" class="back-link">
    <svg viewBox="0 0 20 20" fill="currentColor">
      <path fill-rule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z"/>
    </svg>
    Back to Roster
  </a>

  {# Active Patient Banner #}
  <div
    id="ccow-banner"
    hx-get="/context/banner"
    hx-trigger="load, every 5s"
    hx-swap="outerHTML"
  >
    {% include "partials/ccow_banner.html" %}
  </div>

  {# Patient Demographics Card #}
  <div class="card">
    <div class="card-header">
      <h2 class="card-title">Patient Details</h2>
      <div class="action-buttons">
        <a href="/patients/{{ patient.icn }}/edit" class="btn btn-sm btn-outline">
          <svg class="btn-icon-sm" viewBox="0 0 20 20" fill="currentColor">
            <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/>
          </svg>
          Edit
        </a>
        <button
          class="btn btn-sm btn-primary"
          hx-post="/context/set/{{ patient.icn }}"
          hx-swap="none"
          hx-on::after-request="htmx.trigger('#ccow-banner', 'load')"
        >
          <svg class="btn-icon-sm" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/>
          </svg>
          Set as CCOW
        </button>
      </div>
    </div>

    <div class="card-body">
      <dl class="detail-list">
        <div class="detail-item">
          <dt>Name</dt>
          <dd class="patient-name">{{ patient.name_display }}</dd>
        </div>
        <div class="detail-item">
          <dt>ICN</dt>
          <dd class="font-mono">{{ patient.icn }}</dd>
        </div>
        <div class="detail-item">
          <dt>Date of Birth</dt>
          <dd>
            {{ patient.dob.strftime('%B %d, %Y') if patient.dob else 'N/A' }}
            {% if patient.age %}
            <span class="age-badge">({{ patient.age }} years old)</span>
            {% endif %}
          </dd>
        </div>
        <div class="detail-item">
          <dt>Gender</dt>
          <dd><span class="badge badge-neutral">{{ patient.gender or patient.sex or 'N/A' }}</span></dd>
        </div>
        {% if patient.ssn_last4 %}
        <div class="detail-item">
          <dt>SSN</dt>
          <dd class="font-mono">***-**-{{ patient.ssn_last4 }}</dd>
        </div>
        {% endif %}
        {% if patient.source_system %}
        <div class="detail-item">
          <dt>Data Source</dt>
          <dd>
            <span class="badge {% if patient.source_system == 'med-z4' %}badge-teal{% else %}badge-neutral{% endif %}">
              {{ patient.source_system }}
            </span>
          </dd>
        </div>
        {% endif %}
      </dl>
    </div>
  </div>

  {# Clinical Data Section #}
  <div class="card">
    <div class="card-header">
      <h2 class="card-title">Clinical Data</h2>
    </div>
    <div class="card-body">

      {# Vital Signs Subsection #}
      <div class="clinical-section" x-data="{ open: true }">
        <div class="section-header">
          <button @click="open = !open" class="section-toggle">
            <svg class="section-icon" :class="{ 'rotate-90': open }" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"/>
            </svg>
            <span class="section-title">
              📊 Vital Signs
              <span class="count-badge">{{ vitals|length }}</span>
            </span>
          </button>
          <a href="/patients/{{ patient.icn }}/vitals/new" class="btn btn-sm btn-primary">
            <svg class="btn-icon-sm" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"/>
            </svg>
            Add Vital
          </a>
        </div>

        <div class="section-content" x-show="open" x-collapse>
          {% if vitals %}
          <div class="vitals-list">
            {% for vital in vitals %}
            <div class="vital-item">
              <span class="vital-date">{{ vital.taken_datetime.strftime('%Y-%m-%d %H:%M') }}</span>
              <span class="vital-reading">BP: {{ vital.systolic }}/{{ vital.diastolic }}</span>
              <span class="vital-reading">HR: {{ vital.heart_rate }}</span>
              <span class="vital-reading">Temp: {{ vital.temperature }}°F</span>
              <div class="vital-actions">
                <button
                  class="btn btn-xs btn-danger"
                  hx-delete="/patients/{{ patient.icn }}/vitals/{{ vital.vital_id }}"
                  hx-confirm="Delete this vital sign record?"
                  hx-target="closest .vital-item"
                  hx-swap="outerHTML swap:1s"
                >Delete</button>
              </div>
            </div>
            {% endfor %}
          </div>
          {% else %}
          <p class="empty-hint">No vital signs recorded yet. Click "Add Vital" to create the first entry.</p>
          {% endif %}
        </div>
      </div>

      {# Allergies Subsection #}
      <div class="clinical-section" x-data="{ open: true }">
        <div class="section-header">
          <button @click="open = !open" class="section-toggle">
            <svg class="section-icon" :class="{ 'rotate-90': open }" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"/>
            </svg>
            <span class="section-title">
              ⚠️ Allergies
              <span class="count-badge">{{ allergies|length }}</span>
            </span>
          </button>
          <a href="/patients/{{ patient.icn }}/allergies/new" class="btn btn-sm btn-primary">
            <svg class="btn-icon-sm" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"/>
            </svg>
            Add Allergy
          </a>
        </div>

        <div class="section-content" x-show="open" x-collapse>
          {% if allergies %}
          <div class="allergies-list">
            {% for allergy in allergies %}
            <div class="allergy-item {% if allergy.severity == 'SEVERE' %}severe{% endif %}">
              <div class="allergy-info">
                <span class="allergen-name">{{ allergy.allergen }}</span>
                <span class="severity-badge severity-{{ allergy.severity|lower }}">{{ allergy.severity }}</span>
                <span class="reaction-text">{{ allergy.reactions }}</span>
              </div>
              <div class="allergy-actions">
                <button
                  class="btn btn-xs btn-danger"
                  hx-delete="/patients/{{ patient.icn }}/allergies/{{ allergy.allergy_id }}"
                  hx-confirm="Delete this allergy record?"
                  hx-target="closest .allergy-item"
                  hx-swap="outerHTML swap:1s"
                >Delete</button>
              </div>
            </div>
            {% endfor %}
          </div>
          {% else %}
          <p class="empty-hint">No allergies recorded. Click "Add Allergy" to document an allergy.</p>
          {% endif %}
        </div>
      </div>

      {# Clinical Notes Subsection #}
      <div class="clinical-section" x-data="{ open: true }">
        <div class="section-header">
          <button @click="open = !open" class="section-toggle">
            <svg class="section-icon" :class="{ 'rotate-90': open }" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"/>
            </svg>
            <span class="section-title">
              📝 Clinical Notes
              <span class="count-badge">{{ notes|length }}</span>
            </span>
          </button>
          <a href="/patients/{{ patient.icn }}/notes/new" class="btn btn-sm btn-primary">
            <svg class="btn-icon-sm" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"/>
            </svg>
            Add Note
          </a>
        </div>

        <div class="section-content" x-show="open" x-collapse>
          {% if notes %}
          <div class="notes-list">
            {% for note in notes %}
            <div class="note-item">
              <div class="note-header">
                <span class="note-date">{{ note.reference_datetime.strftime('%Y-%m-%d') }}</span>
                <span class="note-type">{{ note.document_title }}</span>
                <span class="note-author">by {{ note.author_name }}</span>
              </div>
              <p class="note-preview">{{ note.text_preview or (note.document_text[:100] + '...') }}</p>
              <div class="note-actions">
                <a href="/patients/{{ patient.icn }}/notes/{{ note.note_id }}" class="btn btn-xs btn-outline">View</a>
                <button
                  class="btn btn-xs btn-danger"
                  hx-delete="/patients/{{ patient.icn }}/notes/{{ note.note_id }}"
                  hx-confirm="Delete this clinical note?"
                  hx-target="closest .note-item"
                  hx-swap="outerHTML swap:1s"
                >Delete</button>
              </div>
            </div>
            {% endfor %}
          </div>
          {% else %}
          <p class="empty-hint">No clinical notes recorded. Click "Add Note" to create a note.</p>
          {% endif %}
        </div>
      </div>

    </div>
  </div>
</div>
{% endblock %}
```

#### 11.9.4 Vital Signs Form Template (templates/vital_form.html)

```html
{# templates/vital_form.html #}
{% extends "base.html" %}

{% block title %}Add Vital Signs - {{ patient.name_display }}{% endblock %}

{% block content %}
<div class="form-container">
  <a href="/patients/{{ patient.icn }}" class="back-link">
    <svg viewBox="0 0 20 20" fill="currentColor">
      <path fill-rule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z"/>
    </svg>
    Back to Patient
  </a>

  <div class="card">
    <div class="card-header">
      <h2 class="card-title">
        Add Vital Signs
        <span class="patient-context">{{ patient.name_display }}</span>
      </h2>
    </div>

    <div class="card-body">
      <form method="POST" action="/patients/{{ patient.icn }}/vitals/new" class="vitals-form">
        {# Error Summary #}
        <div id="form-errors">
          {% if errors %}{% include "partials/form_errors.html" %}{% endif %}
        </div>

        <div class="form-grid">
          {# Vital Date/Time #}
          <div class="form-group full-width">
            <label for="vital_date" class="form-label required">Measurement Date/Time</label>
            <div class="datetime-group">
              <input type="date" id="vital_date" name="vital_date" class="form-input"
                value="{{ today.strftime('%Y-%m-%d') }}" max="{{ today.strftime('%Y-%m-%d') }}" required>
              <input type="time" id="vital_time" name="vital_time" class="form-input"
                value="{{ now.strftime('%H:%M') if now else '' }}" required>
            </div>
          </div>

          {# Blood Pressure #}
          <div class="form-group full-width">
            <label class="form-label required">Blood Pressure</label>
            <div class="bp-group">
              <div class="bp-input-group">
                <label for="systolic" class="bp-label">Systolic *</label>
                <input type="number" id="systolic" name="systolic" class="form-input bp-input"
                  min="60" max="250" required placeholder="120">
              </div>
              <span class="bp-separator">/</span>
              <div class="bp-input-group">
                <label for="diastolic" class="bp-label">Diastolic *</label>
                <input type="number" id="diastolic" name="diastolic" class="form-input bp-input"
                  min="40" max="150" required placeholder="80">
              </div>
              <span class="unit-label">mmHg</span>
            </div>
          </div>

          {# Heart Rate #}
          <div class="form-group">
            <label for="heart_rate" class="form-label required">Heart Rate</label>
            <div class="input-with-unit">
              <input type="number" id="heart_rate" name="heart_rate" class="form-input"
                min="30" max="250" required placeholder="72">
              <span class="unit-label">bpm</span>
            </div>
          </div>

          {# Temperature #}
          <div class="form-group">
            <label for="temperature" class="form-label required">Temperature</label>
            <div class="input-with-unit">
              <input type="number" id="temperature" name="temperature" class="form-input"
                min="95" max="108" step="0.1" required placeholder="98.6">
              <span class="unit-label">°F</span>
            </div>
          </div>

          {# Respiratory Rate #}
          <div class="form-group">
            <label for="respiratory_rate" class="form-label">
              Respiratory Rate <span class="optional-badge">Optional</span>
            </label>
            <div class="input-with-unit">
              <input type="number" id="respiratory_rate" name="respiratory_rate" class="form-input"
                min="8" max="60" placeholder="16">
              <span class="unit-label">breaths/min</span>
            </div>
          </div>

          {# Oxygen Saturation #}
          <div class="form-group">
            <label for="oxygen_saturation" class="form-label">
              Oxygen Saturation <span class="optional-badge">Optional</span>
            </label>
            <div class="input-with-unit">
              <input type="number" id="oxygen_saturation" name="oxygen_saturation" class="form-input"
                min="70" max="100" placeholder="98">
              <span class="unit-label">%</span>
            </div>
          </div>
        </div>

        <div class="form-actions">
          <a href="/patients/{{ patient.icn }}" class="btn btn-outline">Cancel</a>
          <button type="submit" class="btn btn-primary">Save Vital Signs</button>
        </div>
      </form>
    </div>
  </div>
</div>
{% endblock %}
```

#### 11.9.5 Form Errors Partial (templates/partials/form_errors.html)

```html
{# templates/partials/form_errors.html #}
{% if errors %}
<div class="error-summary">
  <svg class="alert-icon" viewBox="0 0 20 20" fill="currentColor">
    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"/>
  </svg>
  <div>
    <p class="error-title">Please correct the following errors:</p>
    <ul class="error-list">
      {% for error in errors %}
      <li>{{ error }}</li>
      {% endfor %}
    </ul>
  </div>
</div>
{% endif %}
```

### 11.10 HTMX Interaction Patterns (Complete)

This section documents the HTMX patterns used throughout the application for dynamic updates without full page reloads.

#### Pattern 1: CCOW Context Polling

**Use Case**: Auto-refresh CCOW banner every 5 seconds to detect context changes from other applications (e.g., med-z1).

**Implementation**:
```html
<div
  id="ccow-banner"
  hx-get="/context/banner"
  hx-trigger="load, every 5s"
  hx-swap="outerHTML"
>
  <!-- Banner content loaded via HTMX -->
</div>
```

**Attributes**:
- `hx-get="/context/banner"`: GET request to fetch updated banner HTML
- `hx-trigger="load, every 5s"`: Trigger on page load and every 5 seconds
- `hx-swap="outerHTML"`: Replace entire element (preserves `id` for next poll)

**Backend Route**:
```python
@router.get("/context/banner", response_class=HTMLResponse)
async def get_context_banner(
    request: Request,
    user: Dict = Depends(get_current_user)
):
    ccow = CCOWClient(session_id=user["session_id"])
    context = await ccow.get_context()
    
    return templates.TemplateResponse(
        "partials/ccow_banner.html",
        {"request": request, "context": context, "user": user}
    )
```

---

#### Pattern 2: Set CCOW Context (No Page Refresh)

**Use Case**: Set CCOW context when user clicks "Set CCOW" button, refresh banner without full page reload.

**Implementation**:
```html
<button
  class="btn btn-sm btn-primary"
  hx-post="/context/set/{{ patient.icn }}"
  hx-swap="none"
  hx-on::after-request="if(event.detail.successful) { htmx.trigger('#ccow-banner', 'load'); }"
>
  Set as CCOW
</button>
```

**Attributes**:
- `hx-post="/context/set/ICN123"`: POST request to set context
- `hx-swap="none"`: Don't replace button content
- `hx-on::after-request`: Custom JavaScript after request completes
- `htmx.trigger('#ccow-banner', 'load')`: Manually trigger banner refresh

**Backend Route**:
```python
@router.post("/context/set/{patient_icn}")
async def set_context(
    patient_icn: str,
    user: Dict = Depends(get_current_user)
):
    ccow = CCOWClient(session_id=user["session_id"])
    success = await ccow.set_context(patient_icn, set_by="med-z4")
    
    if not success:
        raise HTTPException(status_code=500, detail="CCOW vault error")
    
    return JSONResponse({"success": True, "patient_id": patient_icn})
```

---

#### Pattern 3: Delete with Confirmation and Animation

**Use Case**: Delete a vital sign record with confirmation dialog and fade-out animation.

**Implementation**:
```html
<button
  class="btn btn-xs btn-danger"
  hx-delete="/patients/{{ patient.icn }}/vitals/{{ vital.vital_id }}"
  hx-confirm="Delete this vital sign record?"
  hx-target="closest .vital-item"
  hx-swap="outerHTML swap:1s"
>
  Delete
</button>
```

**Attributes**:
- `hx-delete="/patients/.../vitals/123"`: DELETE request
- `hx-confirm="..."`: Browser confirmation dialog before request
- `hx-target="closest .vital-item"`: Target nearest ancestor with class `vital-item`
- `hx-swap="outerHTML swap:1s"`: Replace element with 1-second transition

**Backend Route**:
```python
@router.delete("/patients/{icn}/vitals/{vital_id}")
async def delete_vital(
    icn: str,
    vital_id: int,
    user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Delete vital from database
    await db.execute(
        delete(PatientVital).where(PatientVital.vital_id == vital_id)
    )
    await db.commit()
    
    # Return empty response (HTMX will remove element)
    return Response(status_code=200, content="")
```

**CSS for Fade Animation**:
```css
.vital-item {
  transition: opacity 1s ease-out;
}

.vital-item.htmx-swapping {
  opacity: 0;
}
```

---

#### Pattern 4: Form Validation with Error Display

**Use Case**: Submit form via HTMX, display server-side validation errors inline without full page reload.

**Implementation**:
```html
<form
  method="POST"
  action="/patients/new"
  hx-post="/patients/new"
  hx-target="#form-errors"
  hx-swap="innerHTML"
>
  <div id="form-errors"></div>
  
  <div class="form-group">
    <label for="first_name" class="form-label required">First Name</label>
    <input type="text" id="first_name" name="first_name" class="form-input" required>
  </div>
  
  <!-- More fields... -->
  
  <button type="submit" class="btn btn-primary">Create Patient</button>
</form>
```

**Backend Route (Success)**:
```python
@router.post("/patients/new")
async def create_patient(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    date_of_birth: date = Form(...),
    gender: str = Form(...),
    user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Validation passed, create patient
    icn = await generate_unique_icn(db)
    patient = PatientDemographics(
        patient_key=icn,
        icn=icn,
        name_first=first_name,
        name_last=last_name,
        dob=date_of_birth,
        sex=gender,
        source_system="med-z4"
    )
    db.add(patient)
    await db.commit()
    
    # Redirect to patient detail page
    return RedirectResponse(url=f"/patients/{icn}", status_code=303)
```

**Backend Route (Validation Error)**:
```python
@router.post("/patients/new")
async def create_patient(request: Request, ...):
    errors = []
    
    if not first_name:
        errors.append("First name is required")
    if not last_name:
        errors.append("Last name is required")
    
    if errors:
        # Return error HTML fragment (HTMX will inject into #form-errors)
        return templates.TemplateResponse(
            "partials/form_errors.html",
            {"request": request, "errors": errors},
            status_code=422
        )
    
    # ... create patient
```

---

#### Pattern 5: Out-of-Band Swaps (Multiple Updates)

**Use Case**: Update multiple page sections from a single HTMX request (e.g., update patient count AND table after creating new patient).

**Implementation**:
```html
<div id="patient-table" hx-target="this" hx-swap="outerHTML">
  <!-- Table content -->
</div>

<div id="patient-count">
  Total: <span>4</span>
</div>
```

**Backend Route**:
```python
@router.post("/patients/quick-add")
async def quick_add_patient(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # Create patient...
    
    # Get updated data
    result = await db.execute(select(PatientDemographics))
    patients = result.scalars().all()
    
    # Render main table
    table_html = templates.TemplateResponse(
        "partials/patient_table.html",
        {"request": request, "patients": patients}
    ).body.decode()
    
    # Render OOB count update
    count_html = f'<div id="patient-count" hx-swap-oob="true">Total: <span>{len(patients)}</span></div>'
    
    return HTMLResponse(table_html + count_html)
```

**Learning Note**: `hx-swap-oob="true"` tells HTMX to update elements with matching IDs anywhere on the page, not just the target element.

---

#### Pattern 6: Lazy Loading Content

**Use Case**: Load clinical notes only when user expands the notes section (reduces initial page load).

**Implementation**:
```html
<div class="clinical-section" x-data="{ open: false, loaded: false }">
  <div class="section-header">
    <button 
      @click="open = !open; if(!loaded) { $refs.notesContent.dispatchEvent(new Event('load-notes')); loaded = true; }"
      class="section-toggle"
    >
      📝 Clinical Notes
    </button>
  </div>
  
  <div 
    x-ref="notesContent"
    x-show="open" 
    hx-get="/patients/{{ patient.icn }}/notes"
    hx-trigger="load-notes"
    hx-swap="innerHTML"
  >
    <p class="loading">Loading notes...</p>
  </div>
</div>
```

**Explanation**:
- Notes are not loaded on initial page render
- When user clicks to expand, Alpine.js dispatches `load-notes` event
- HTMX listens for this event and fetches notes
- `loaded` flag prevents re-fetching on subsequent toggles

---

### 11.11 UI/UX Best Practices

#### Accessibility (508 Compliance)

1. **Semantic HTML**:
   - Use `<button>` for actions, `<a>` for navigation
   - Proper heading hierarchy (`<h1>` → `<h2>` → `<h3>`)
   - `<label>` elements with `for` attribute for all form inputs

2. **Keyboard Navigation**:
   - All interactive elements accessible via Tab key
   - Visible focus states (teal outline)
   - Skip links for screen readers

3. **Color Contrast**:
   - All text meets WCAG AA standards (4.5:1 for body text, 3:1 for large text)
   - Never rely on color alone (use icons + text)

4. **ARIA Attributes** (when needed):
   - `role="alert"` for error messages
   - `aria-label` for icon-only buttons
   - `aria-live="polite"` for CCOW status updates

#### Performance Considerations

1. **HTMX Polling**:
   - Limit polling to 5-second intervals (balance freshness vs. server load)
   - Use `hx-swap="outerHTML"` to avoid memory leaks
   - Cache CCOW responses for 1-2 seconds on backend

2. **Image/Icon Strategy**:
   - Inline SVG for icons (better than icon fonts)
   - No external dependencies beyond HTMX and Alpine.js

3. **CSS Organization**:
   - Separate CSS files per page type (login, dashboard, forms)
   - Common styles in `style.css`
   - CSS variables for theme consistency

#### Responsive Design

1. **Breakpoints**:
   - Mobile: < 640px (single column, stacked buttons)
   - Tablet: 640px - 1024px (2-column grid where appropriate)
   - Desktop: > 1024px (full layout)

2. **Mobile-Specific Adjustments**:
   - Larger touch targets (44px minimum)
   - Horizontal scroll for wide tables
   - Collapsible navigation

#### Error Handling UX

1. **Form Validation**:
   - Client-side: HTML5 `required`, `pattern`, `min`, `max`
   - Server-side: FastAPI validation with clear error messages
   - Display: Error summary at top + inline field errors

2. **Network Errors**:
   - HTMX error handling via `hx-on::error`
   - Show user-friendly message on network failure
   - Auto-retry for polling requests

3. **CCOW Errors**:
   - Display "Vault Offline" status
   - Allow manual refresh
   - Graceful degradation (app works without CCOW)

### 11.12 Component Library

Reusable components available:
- Buttons (`.btn`, `.btn-primary`, `.btn-sm`, `.btn-danger`)
- Alerts (`.alert`, `.alert-error`, `.alert-success`)
- Form controls (`.form-group`, `.form-input`)
- Cards and panels
- Tables with striped rows
- CCOW banner and debug panel

#### CCOW Debug Panel

**Purpose:** Show CCOW vault status and context details for debugging during development. Displays in the bottom-right corner of the screen.

**Route:** `GET /context/debug` (HTMX partial, polled every 5 seconds)

**Template (templates/partials/ccow_debug_panel.html):**

```html
{# templates/partials/ccow_debug_panel.html #}
{# CCOW debug panel (optional, bottom-right corner) #}

<div id="ccow-debug-panel" class="ccow-debug-panel"
     hx-get="/context/debug"
     hx-trigger="load, every 5s"
     hx-swap="outerHTML">
    <div class="debug-header">CCOW Status</div>
    <div class="debug-row">
        <span class="debug-label">Vault:</span>
        <span class="debug-value">
            {% if vault_healthy %}
                <span class="status-indicator online"></span> Online
            {% else %}
                <span class="status-indicator offline"></span> Offline
            {% endif %}
        </span>
    </div>
    <div class="debug-row">
        <span class="debug-label">Context ID:</span>
        <span class="debug-value">
            {% if context and context.patient_id %}
                {{ context.patient_id }}
            {% else %}
                None
            {% endif %}
        </span>
    </div>
    <div class="debug-row">
        <span class="debug-label">Set By:</span>
        <span class="debug-value">
            {% if context and context.set_by %}
                {{ context.set_by }}
            {% else %}
                —
            {% endif %}
        </span>
    </div>
    <div class="debug-row">
        <span class="debug-label">Last Sync:</span>
        <span class="debug-value">
            <span id="sync-timestamp">Just now</span>
        </span>
    </div>
</div>
```

**CSS (add to static/css/style.css):**

```css
/* CCOW Debug Panel */
.ccow-debug-panel {
    position: fixed;
    bottom: 1rem;
    right: 1rem;
    background: white;
    border: 2px solid var(--primary-teal);
    border-radius: 8px;
    padding: 1rem;
    font-size: var(--text-sm);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    min-width: 250px;
    z-index: 1000;
}

.debug-header {
    font-weight: 600;
    color: var(--primary-teal);
    margin-bottom: 0.75rem;
    border-bottom: 1px solid var(--gray-200);
    padding-bottom: 0.5rem;
}

.debug-row {
    display: flex;
    justify-content: space-between;
    padding: 0.25rem 0;
}

.debug-label {
    color: var(--gray-500);
    font-weight: 500;
}

.debug-value {
    color: var(--gray-900);
    font-family: 'Courier New', monospace;
}

.status-indicator {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 0.25rem;
    vertical-align: middle;
}

.status-indicator.online {
    background-color: var(--success-green);
}

.status-indicator.offline {
    background-color: var(--danger-red);
}
```

**Route Handler (add to app/routes/context.py):**

```python
@router.get("/debug", response_class=HTMLResponse)
async def get_ccow_debug_panel(
    request: Request,
    user: Dict = Depends(get_current_user)
):
    """
    Get CCOW debug panel (HTMX partial).

    GET /context/debug

    Returns HTML fragment showing CCOW vault status and current context.
    Polled every 5 seconds for real-time updates.
    """
    ccow = CCOWClient(session_id=user["session_id"])
    context = await ccow.get_context()
    vault_healthy = await ccow.health_check()

    return templates.TemplateResponse("partials/ccow_debug_panel.html", {
        "request": request,
        "context": context,
        "vault_healthy": vault_healthy,
        "user": user,
    })
```

**Usage in Dashboard (add to templates/dashboard.html before closing `{% endblock %}`):**

```html
{# CCOW Debug Panel (optional, bottom-right corner) #}
<div id="ccow-debug-panel"
     hx-get="/context/debug"
     hx-trigger="load, every 5s"
     hx-swap="outerHTML">
    {% include "partials/ccow_debug_panel.html" %}
</div>
```

**Template Variables:**

| Variable | Type | Description |
|----------|------|-------------|
| `vault_healthy` | bool | True if CCOW vault health check passed |
| `context` | dict \| None | Current CCOW context (patient_id, set_by) |
| `user` | dict | Current user info |

**Verification:**
- Debug panel appears in bottom-right corner of dashboard
- Shows "Online" with green indicator when vault is running
- Shows "Offline" with red indicator when vault is stopped
- Context ID updates when patient is selected
- Panel refreshes every 5 seconds via HTMX polling

---


## 12. Testing Strategy

### 12.1 Manual Testing Checklist

**Authentication:**
- [ ] Login with valid credentials succeeds
- [ ] Login with invalid password fails (shows error)
- [ ] Logout clears session cookie
- [ ] Accessing /dashboard without login redirects to /login
- [ ] Session expires after 25 minutes (requires re-login)

**CCOW Context Synchronization:**
- [ ] Selecting patient in med-z4 updates med-z1 context
- [ ] Selecting patient in med-z1 updates med-z4 context
- [ ] Context changes visible within 5 seconds (HTMX polling)
- [ ] Clear context in either app clears both

**Patient CRUD:**
- [ ] New patient form validates required fields
- [ ] Creating patient generates unique 999 series ICN
- [ ] New patient appears in roster immediately
- [ ] Duplicate ICN creation prevented

**Clinical Data CRUD:**
- [ ] Adding vital for patient succeeds
- [ ] Vital appears in med-z1 Vitals widget
- [ ] Adding allergy increases med-z1 allergy count
- [ ] Clinical note appears in med-z1 Notes page
- [ ] med-z4-created data tagged with source_system='med-z4'

### 12.2 Database Verification Queries

```sql
-- Verify med-z4 created patients
SELECT patient_key, icn, name_display, source_system
FROM clinical.patient_demographics
WHERE icn LIKE '999V%'
ORDER BY last_updated DESC
LIMIT 10;

-- Verify med-z4 sessions
SELECT s.session_id, u.email, s.created_at, s.expires_at
FROM auth.sessions s
JOIN auth.users u ON s.user_id = u.user_id
WHERE s.is_active = TRUE;

-- Verify CCOW-related audit logs
SELECT *
FROM auth.audit_logs
WHERE event_type IN ('ccow_set', 'ccow_clear')
ORDER BY event_timestamp DESC
LIMIT 20;
```

---

## 13. Known Limitations & Future Enhancements

### 13.1 Phase 1-8 Limitations

**Sandcastle Data:**
- Data created in med-z4 is **ephemeral** (wiped by med-z1 ETL runs)
- No persistence guarantee beyond test session
- **Mitigation:** Document clearly in UI ("Test Data - Not Persistent")

**No Update/Delete:**
- Phase 1-8 only supports CREATE operations
- Cannot edit or delete existing records
- **Future:** Add PATCH /patients/{icn}, DELETE /patients/{icn}

**Limited Validation:**
- Minimal business logic validation (relies on database constraints)
- No duplicate name checking
- **Future:** Add validation layer (Pydantic schemas)

### 13.2 Future Enhancements (Post-Phase 8)

| Phase | Feature | Description |
|-------|---------|-------------|
| 9 | Advanced CRUD | Update/delete patients and clinical data |
| 10 | Data Validation | Pydantic schemas, business rules |
| 11 | Search & Filter | Full-text search, demographic filters, pagination |
| 12 | Audit Trail UI | View all data creation events in med-z4 |
| 13 | ETL Integration | Protected data that survives ETL refreshes |

---

## 14. Deployment Considerations

### 14.1 Development Environment

**Current Setup (Phase 1-8):**
- med-z4 runs on developer laptop (localhost:8005)
- Shares PostgreSQL with med-z1 (localhost:5432)
- CCOW vault on localhost:8001
- Single user testing

**Requirements:**
- Python 3.11 (macOS) / 3.10 (Linux)
- PostgreSQL 16 (Docker container)
- 2 GB RAM minimum
- Port 8005 available

### 14.2 Production Security Hardening

**Required for Production:**

- [ ] Enable CSRF protection on all forms
- [ ] Implement rate limiting (login: 5/min, API: 100/min)
- [ ] Add account lockout after 5 failed login attempts
- [ ] Enforce HTTPS only (no HTTP)
- [ ] Require TLS for database connections (`sslmode=require`)
- [ ] Add security headers middleware
- [ ] Use dedicated `med_z4_app` database role (not `postgres`)
- [ ] Enable audit logging for all clinical data access
- [ ] Set secure cookie flags: `secure=True`, `httponly=True`, `samesite='strict'`
- [ ] Disable FastAPI auto-docs in production (`docs_url=None`)
- [ ] Set strong `SECRET_KEY` (64+ random characters)

---

## 15. References

### Related Documentation

**med-z1 Architecture & Design:**
- `docs/spec/med-z1-architecture.md` - System architecture and design patterns
- `docs/spec/postgresql-database-reference.md` - Complete PostgreSQL schema reference
- `docs/guide/developer-setup-guide.md` - Development environment setup

**CCOW Implementation:**
- `ccow/README.md` - CCOW Context Vault overview
- `ccow/main.py` - CCOW vault v2.0 REST API implementation

### External Resources

| Resource | URL |
|----------|-----|
| FastAPI Documentation | https://fastapi.tiangolo.com/ |
| HTMX Documentation | https://htmx.org/docs/ |
| SQLAlchemy Documentation | https://docs.sqlalchemy.org/ |
| PostgreSQL Documentation | https://www.postgresql.org/docs/16/ |
| bcrypt Best Practices | https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html |

---

## 16. Glossary

| Term | Definition |
|------|------------|
| **CCOW** | Clinical Context Object Workgroup - HL7 standard for synchronizing clinical application context |
| **ICN** | Integration Control Number - Unique patient identifier in VA systems (format: digits + "V" + digits) |
| **patient_key** | Primary key in clinical tables - currently equals ICN but may diverge in future |
| **Context Vault** | Central service that stores and distributes the currently active patient for each user |
| **Sandcastle Data** | Ephemeral test data created in med-z4 that may be wiped by ETL refreshes |
| **999 Series** | ICN prefix (999V######) used to identify med-z4-created test patients |
| **source_system** | Database column indicating data origin ('ETL', 'med-z4', 'VistA-RPC') |
| **HTMX** | JavaScript library enabling dynamic UI updates via HTML attributes |
| **Partial Template** | Small HTML fragment returned by server for HTMX to swap into page |
| **Session Cookie** | Browser cookie storing session ID for authentication |
| **bcrypt** | Password hashing algorithm designed to be slow (resists brute-force attacks) |

---

## Appendix A: Quick Reference Commands

### Development Workflow

```bash
# Start med-z4 (from project root)
cd ~/swdev/med/med-z4
source .venv/bin/activate
uvicorn main:app --port 8005 --reload

# Start CCOW vault (separate terminal)
cd ~/swdev/med/med-z1
source .venv/bin/activate
uvicorn ccow.main:app --port 8001 --reload

# Start med-z1 (separate terminal)
cd ~/swdev/med/med-z1
source .venv/bin/activate
uvicorn app.main:app --port 8000 --reload

# Access applications
# med-z4: http://localhost:8005
# med-z1: http://localhost:8000
# CCOW vault: http://localhost:8001/docs
```

### Database Queries

```sql
-- List all med-z4 test patients
SELECT icn, name_display, dob, age, source_system
FROM clinical.patient_demographics
WHERE source_system = 'med-z4'
ORDER BY last_updated DESC;

-- Check active sessions
SELECT s.session_id, u.email, s.created_at, s.expires_at
FROM auth.sessions s
JOIN auth.users u ON s.user_id = u.user_id
WHERE s.is_active = TRUE;
```

### Testing CCOW with curl

```bash
# Health check
curl http://localhost:8001/ccow/health

# Get context (requires session cookie)
curl -b "med_z4_session_id=your-session-uuid" \
  http://localhost:8001/ccow/active-patient

# Set context
curl -X PUT \
  -b "med_z4_session_id=your-session-uuid" \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"999V123456","set_by":"med-z4"}' \
  http://localhost:8001/ccow/active-patient
```

---

## Appendix B: Troubleshooting Guide

### Issue: CSS Not Loading

**Symptoms:** Page displays but no Teal theme, plain HTML

**Solutions:**
1. Check static files are mounted: `app.mount("/static", ...)`
2. Verify CSS files exist in `static/css/` directory
3. Check browser Network tab for 404 errors
4. Ensure paths start with `/static/` not `static/`

### Issue: HTMX Not Working

**Symptoms:** Buttons don't do anything, no polling

**Solutions:**
1. Check HTMX script is included in `<head>` of base.html
2. Open browser console, look for JavaScript errors
3. Check Network tab - should see XHR requests every 5 seconds
4. Verify backend routes return HTML, not JSON

### Issue: Database Connection Failed

**Symptoms:** Application won't start, database errors

**Solutions:**
1. Verify PostgreSQL is running: `docker ps`
2. Check credentials in `.env` file
3. Test connection: `psql -h localhost -U postgres -d medz1`
4. Verify `asyncpg` is installed: `pip install asyncpg`

### Issue: Session Invalid After Login

**Symptoms:** Login succeeds but immediately redirects back to login

**Solutions:**
1. Check cookie is being set (browser dev tools > Application > Cookies)
2. Verify SESSION_SECRET_KEY is at least 32 characters
3. Check session timeout hasn't expired immediately
4. Verify session was created in database: `SELECT * FROM auth.sessions`

### Issue: CCOW Context Not Syncing

**Symptoms:** Select patient but med-z1 doesn't update

**Solutions:**
1. Verify CCOW vault is running on port 8001
2. Check both apps are using same user (same user_id in vault)
3. Verify session cookie is valid for CCOW vault
4. Check vault logs for errors

---

## Appendix C: Template Variable Reference

### login.html
| Variable | Type | Description |
|----------|------|-------------|
| `error` | string \| None | Error message to display |

### dashboard.html
| Variable | Type | Description |
|----------|------|-------------|
| `user` | dict | Current user info (user_id, email, display_name) |
| `patients` | list[PatientDemographics] | All patients from database |
| `context` | dict \| None | Current CCOW context (patient_id, set_by) |

### patient_detail.html
| Variable | Type | Description |
|----------|------|-------------|
| `user` | dict | Current user info |
| `patient` | PatientDemographics | Patient record |
| `vitals` | list[PatientVital] | Recent vitals (limit 10) |
| `allergies` | list[PatientAllergy] | All allergies |
| `notes` | list[ClinicalNote] | Recent notes (limit 10) |

### patient_form.html
| Variable | Type | Description |
|----------|------|-------------|
| `user` | dict | Current user info |
| `patient` | PatientDemographics \| None | Patient for edit, None for create |
| `today` | date | Current date for DOB validation |
| `errors` | dict \| None | Field validation errors |

### partials/ccow_banner.html
| Variable | Type | Description |
|----------|------|-------------|
| `context` | dict \| None | Current CCOW context |
| `user` | dict | Current user info |

### partials/ccow_debug_panel.html
| Variable | Type | Description |
|----------|------|-------------|
| `vault_healthy` | bool | True if CCOW vault health check passed |
| `context` | dict \| None | Current CCOW context (patient_id, set_by) |
| `user` | dict | Current user info |

---

**End of Design Specification**


