# med-z4 (Simple EHR) – Design Specification

**Document Version:** v1.0  
**Date:** January 22, 2026  
**Repository:** `med-z4`  
**Status:** Final Design - Ready for Implementation  
**Author:** Chuck Sylvester  

---

## Document Purpose

This comprehensive design specification provides complete technical guidance for implementing med-z4, a standalone "Simple EHR" application that serves as a CCOW participant and clinical data management tool for the med-z1 ecosystem.

**Target Audience:** Developers implementing med-z4 from scratch with educational explanations for learning FastAPI, HTMX, PostgreSQL, and CCOW patterns.

**Scope:** This document covers Phases 1-8 implementation (authentication, CCOW integration, patient roster, CRUD operations for clinical data).

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Repository Structure](#3-repository-structure)
4. [Configuration Management](#4-configuration-management)
5. [Database Design & Schema Sharing](#5-database-design--schema-sharing)
   - 5.7 Database Access Model & Permissions ⭐ **NEW**
   - 5.8 Patient Identity: patient_key vs icn ⭐ **NEW**
6. [Authentication Design](#6-authentication-design)
   - 6.7 Audit Logging: Clinical Data Access ⭐ **NEW**
7. [CCOW Context Management](#7-ccow-context-management)
   - 7.5 Session Cookie Contract with CCOW Vault ⭐ **NEW**
8. [Core Features (Phase 1-5)](#8-core-features-phase-1-5)
9. [Clinical Data Management (CRUD) - Phase 6-8](#9-clinical-data-management-crud---phase-6-8)
   - 9.8 Data Ownership & ETL Interaction ⭐ **NEW**
10. [Implementation Roadmap](#10-implementation-roadmap)
11. [Testing Strategy](#11-testing-strategy)
12. [Known Limitations & Future Enhancements](#12-known-limitations--future-enhancements)
13. [Deployment Considerations](#13-deployment-considerations)
   - 13.5 Security Hardening for Production ⭐ **NEW**
14. [References](#14-references)
15. [UI/UX Design & Wireframes](#15-uiux-design--wireframes)
16. [**🎯 Implementation Mapping: Roadmap ↔ UI/UX**](#16-implementation-mapping-roadmap--uiux)
   - 16.1 Routes and Templates Contract ⭐ **NEW**

---

## 1. Executive Summary

### 1.1 Purpose

**med-z4** is a standalone "Simple EHR" application designed to simulate a primary Electronic Health Record system. Its role in the med-z1 ecosystem is to act as a **CCOW Participant** that validates multi-application patient context synchronization with the med-z1 longitudinal viewer.

Unlike med-z1 (which is a specialized read-only viewer), med-z4 simulates the "source of truth" workflow where a clinician actively manages patient data. It demonstrates that when a user changes patients in med-z4, the context automatically propagates to med-z1 via the central CCOW Context Vault, and vice versa.

**Key Distinction:** med-z4 is both a **context driver** (setting patient context) and a **data factory** (creating/editing clinical data directly in the PostgreSQL serving database).

### 1.2 Design Philosophy

This design specification follows a **production-ready, learning-focused approach**:

- **Production-Ready:** Full password authentication, secure session management, proper database transactions, error handling
- **Educational:** Extensive technical explanations, learning notes, and implementation guidance for developers new to FastAPI/HTMX/PostgreSQL patterns
- **Incremental:** Clear phased implementation (Phases 1-8) from foundation to full CRUD capabilities
- **Self-Sufficient:** Separate repository with independent configuration, avoiding complex dependencies on med-z1 codebase

### 1.3 Key Objectives

1. **Repository Isolation:** Operate as a completely self-sufficient application in the `med-z4` repository
2. **Shared Identity:** Connect to the existing med-z1 PostgreSQL database (`medz1`) to utilize the same `auth` and `clinical` schemas
3. **Context Interoperability:** Implement full CCOW operations (Get, Set, Clear) with proper authentication
4. **Production-Grade Authentication:** Bcrypt password hashing, secure session cookies, session expiration handling
5. **Clinical Data Management:** CRUD operations for patients, vitals, allergies, notes, and other clinical domains
6. **Visual Distinction:** Teal/Emerald theme to clearly differentiate from med-z1's Blue/Slate theme

### 1.4 Success Criteria

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
| **Service Port** | `8005` | Distinct from med-z1 (8000), CCOW Vault (8001), VistA RPC Broker (8003) |
| **Database Host** | `localhost:5432` | Shared PostgreSQL instance running in Docker |
| **Database Name** | `medz1` | Same database as med-z1 (shared schemas) |
| **Database User** | `postgres` | Shared credential (from `.env` file) |
| **CCOW Vault URL** | `http://localhost:8001` | Targets existing CCOW Context Vault service |
| **Session Cookie Name** | `med_z4_session_id` | **Different from med-z1** to enable independent sessions |
| **Session Timeout** | 25 minutes | Matches med-z1 default (configurable) |
| **Cookie Security** | `HttpOnly=True`, `SameSite=Lax` | Production-ready security settings |

**Key Decision: Separate Session Cookies**

med-z4 uses a **different session cookie name** (`med_z4_session_id`) than med-z1 (`session_id`) for the following reasons:

1. **Independent Testing:** Allows a user to log into both applications simultaneously with different user accounts (useful for testing multi-user CCOW scenarios)
2. **Session Isolation:** Prevents accidental session conflicts or overwrites
3. **Production Realism:** Simulates real-world scenario where different EHR systems maintain separate sessions
4. **Security:** Each application validates its own sessions independently

**Trade-off:** User must log in separately to each application. This is acceptable and realistic for enterprise healthcare systems.

### 2.3 Technology Stack

med-z4 uses the **exact same technology stack** as med-z1 for consistency and learning transfer:

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

**Learning Note: Why This Stack?**

- **FastAPI:** Modern, fast, automatic API documentation, type hints, async support
- **Jinja2:** Mature templating with inheritance, macros, filters (Django-like syntax)
- **HTMX:** Server-side rendering with SPA-like UX (no complex JavaScript build tooling)
- **Starlette Sessions:** Built-in encrypted cookie sessions (no Redis/database needed for Phase 1)
- **SQLAlchemy:** Industry-standard Python ORM with raw SQL support when needed
- **bcrypt:** Industry-standard password hashing (slow by design to resist brute-force attacks)

---

## 3. Repository Structure

med-z4 follows a **flat, simple structure** optimized for learning and rapid development:

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
├── app/                                # Application code (models, routes, services)
│   ├── __init__.py
│   │
│   ├── models/                         # Database models (SQLAlchemy/Pydantic)
│   │   ├── __init__.py
│   │   ├── auth.py                     # User, Session models (matches med-z1 auth schema)
│   │   └── clinical.py                 # Clinical models (Patient, Vital, Allergy, Note)
│   │
│   ├── routes/                         # FastAPI route handlers (endpoints)
│   │   ├── __init__.py
│   │   ├── auth.py                     # Login, logout, session management
│   │   ├── dashboard.py                # Patient roster, dashboard
│   │   ├── context.py                  # CCOW context operations (get/set/clear)
│   │   └── crud.py                     # Patient/clinical data CRUD operations (Phase 6+)
│   │
│   ├── services/                       # Business logic layer
│   │   ├── __init__.py
│   │   ├── auth_service.py             # Password verification, session creation
│   │   ├── ccow_client.py              # CCOW Vault HTTP client
│   │   └── patient_service.py          # Patient data operations (Phase 6+)
│   │
│   └── middleware/                     # Custom middleware (if needed)
│       └── __init__.py
│
├── templates/                          # Jinja2 HTML templates
│   ├── base.html                       # Base layout with Teal theme
│   ├── login.html                      # Login form with password input
│   ├── dashboard.html                  # Patient roster table
│   ├── patient_create.html             # New patient form (Phase 6+)
│   ├── patient_detail.html             # Patient detail page with tabs (Phase 6+)
│   │
│   └── partials/                       # HTMX partial templates (fragments)
│       ├── patient_row.html            # Single patient table row
│       ├── active_patient_banner.html  # Top banner with active patient
│       ├── ccow_debug_panel.html       # CCOW status widget
│       └── forms/                      # Reusable form components (Phase 6+)
│           ├── vital_form.html
│           ├── allergy_form.html
│           └── note_form.html
│
└── static/                             # Static assets (CSS, JS, images)
    ├── css/
    │   └── style.css                   # Custom CSS with Teal theme
    ├── js/
    │   └── htmx.min.js                 # HTMX library (1.9.x)
    └── images/
        └── logo-teal.png               # med-z4 logo, favicon, and other images
```

**Learning Note: Directory Structure Rationale**

- **Flat Structure:** Easier to navigate for learning (vs. deeply nested packages)
- **models/:** Separates database models from business logic (Single Responsibility Principle)
- **routes/:** One file per major feature area (keeps route files manageable)
- **services/:** Business logic extracted from routes (testable, reusable)
- **templates/partials/:** HTMX pattern - small HTML fragments for dynamic updates
- **static/:** Public assets served directly by FastAPI StaticFiles middleware

**Python Module Imports:**

With this structure, imports look like:
```python
from app.models.auth import User, Session
from app.services.auth_service import verify_password, create_session
from app.services.ccow_client import CCOWClient
```

---

## 4. Configuration Management

### 4.1 Environment Variables (.env)

The `.env` file stores all configuration and secrets. **Never commit this file to Git.**

**Template (.env.example):**

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

**Learning Note: Environment Variable Best Practices**

- **Never hardcode secrets:** Database passwords, session keys must be in `.env`
- **Use .env.example:** Commit a template with placeholder values for documentation
- **Prefix by concern:** Group related settings (SESSION_*, POSTGRES_*, CCOW_*)
- **Document units:** `SESSION_TIMEOUT_MINUTES` is clear (vs. ambiguous `SESSION_TIMEOUT`)
- **Separate by environment:** Use `.env.dev`, `.env.prod` for different deployments

### 4.2 Configuration Loader (config.py)

Centralized configuration module that loads and validates environment variables:

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
SESSION_COOKIE_MAX_AGE = SESSION_TIMEOUT_MINUTES * 60  # Convert to seconds
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "med_z4_session_id")

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

# SQLAlchemy connection string
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

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

**Learning Note: Configuration Pattern**

1. **Fail Fast:** Raise errors on startup if required config is missing (don't fail later during runtime)
2. **Type Conversion:** Convert strings to int/bool where needed (`int(os.getenv(...))`)
3. **Sensible Defaults:** Provide defaults for non-sensitive settings (port, timeout)
4. **Validation:** Check constraints (e.g., secret key length) before app starts
5. **Single Import:** Other modules import from `config` (not `os.getenv` scattered everywhere)

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

SQLAlchemy engine and session factory for PostgreSQL connections:

```python
# database.py
# Database connection management for med-z4
# Uses SQLAlchemy 2.x with connection pooling

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from typing import Generator
import logging

from config import DATABASE_URL, DEBUG

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Database Engine (Singleton)
# ---------------------------------------------------------------------

engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,  # Simple pooling for development
    echo=DEBUG,  # Log SQL queries if DEBUG=True
    future=True,  # Use SQLAlchemy 2.x style
)

# Session factory (creates new Session objects)
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)

# ---------------------------------------------------------------------
# Session Dependency for FastAPI
# ---------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session.

    Usage in routes:
        @app.get("/patients")
        def list_patients(db: Session = Depends(get_db)):
            patients = db.query(Patient).all()
            return patients

    The session is automatically closed after the request completes,
    even if an exception occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------------------
# Context Manager for Scripts (Optional)
# ---------------------------------------------------------------------

@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions in non-FastAPI code.

    Usage:
        with get_db_context() as db:
            patient = db.query(Patient).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

**Learning Note: SQLAlchemy Session Pattern**

- **Engine (Singleton):** Created once at module import, reused for all connections
- **SessionLocal (Factory):** Creates new Session objects for each request
- **get_db (Dependency):** FastAPI will call this for every request, automatically closing sessions
- **Connection Pooling:** NullPool for development (simple), use QueuePool in production
- **echo=DEBUG:** Logs SQL queries to console when DEBUG=True (useful for learning)

**Why Not Use SQLModel?**

med-z1 uses SQLAlchemy directly. For consistency and learning transfer, med-z4 uses the same approach. SQLModel (built on SQLAlchemy) is a valid alternative but adds another layer to learn.

---

### 5.7 Database Access Model & Permissions

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

-- Auth schema: INSERT only (create sessions), SELECT (validate sessions)
GRANT SELECT ON auth.users TO med_z4_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON auth.sessions TO med_z4_app;
GRANT INSERT ON auth.audit_logs TO med_z4_app;

-- Clinical schema: Full CRUD on patient-created data
GRANT SELECT, INSERT, UPDATE, DELETE ON clinical.patient_demographics TO med_z4_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON clinical.patient_vitals TO med_z4_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON clinical.patient_allergies TO med_z4_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON clinical.clinical_notes TO med_z4_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON clinical.patient_immunizations TO med_z4_app;

-- Clinical schema: SELECT only on reference/lookup tables
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
| `clinical` | patient_immunizations | SELECT | **INSERT, UPDATE, DELETE** | med-z4 records immunizations |
| `clinical` | patient_encounters | SELECT | SELECT | ETL-sourced only (read-only for both) |
| `clinical` | patient_medications | SELECT | SELECT | ETL-sourced only (read-only for both) |
| `clinical` | patient_labs | SELECT | SELECT | ETL-sourced only (read-only for both) |
| `reference` | All tables | SELECT | SELECT | Reference data (read-only for all apps) |

**Why This Matters:**
- **Principle of Least Privilege:** med-z4 can only modify tables it legitimately needs to edit
- **Prevents Accidental Data Corruption:** Can't accidentally UPDATE ETL-sourced tables (encounters, labs, medications)
- **Audit Trail:** Separate role makes it clear in DB logs which app performed which action
- **Production Safety:** Limits blast radius if med-z4 is compromised

**Configuration Update:**

`.env` file for med-z4 production:
```bash
# Development (shared with med-z1)
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/medz1

# Production (dedicated role)
DATABASE_URL=postgresql://med_z4_app:<secure-password>@db-server:5432/medz1
```

**Implementation Note for Developer:**
- Phase 1-5: Use shared `postgres` user (development simplicity)
- Phase 8: Test with `med_z4_app` role to catch permission issues before prod deployment
- Document role creation SQL in `db/ddl/create_med_z4_app_role.sql`

---

### 5.8 Patient Identity: patient_key vs icn

**Current State:**
The PostgreSQL database uses both `patient_key` and `icn` columns in `clinical.patient_demographics`. Currently, these are **synonyms** (same value), but this may change in future if identity resolution becomes more complex.

**Canonical Rule for med-z4:**

> **Use `patient_key` as the canonical patient identifier in all database queries. Treat `icn` as a display/search field.**

**Why This Matters:**
- Future-proofs for identity resolution scenarios where 1 patient = multiple ICNs
- Matches med-z1 pattern (med-z1 uses `patient_key` internally)
- PostgreSQL foreign keys reference `patient_key`, not `icn`

**Implementation Guidance:**

1. **Database Queries:** Always filter/join on `patient_key`:
   ```python
   # ✅ Correct
   result = await db.execute(
       select(PatientDemographics).where(PatientDemographics.patient_key == icn)
   )

   # ❌ Avoid (unless specifically searching by ICN display value)
   result = await db.execute(
       select(PatientDemographics).where(PatientDemographics.icn == icn)
   )
   ```

2. **URL Routes:** Use `icn` in URLs for readability (user-facing):
   ```python
   @app.get("/patients/{icn}")
   async def patient_detail(icn: str):
       # Convert icn (URL param) to patient_key (DB query)
       patient = await db.execute(
           select(PatientDemographics).where(PatientDemographics.patient_key == icn)
       )
   ```

3. **CCOW Context:** Set context using `icn` (human-readable identifier):
   ```python
   await ccow_client.set_context(patient.icn)  # ✅ Use icn for CCOW
   ```

4. **Foreign Keys:** All clinical tables use `patient_key` (NOT `icn`):
   ```python
   # clinical.patient_vitals
   patient_key = Column(String(50), ForeignKey("clinical.patient_demographics.patient_key"))
   ```

**Summary Table:**

| Use Case | Field to Use | Rationale |
|----------|-------------|-----------|
| Database queries (WHERE, JOIN) | `patient_key` | Primary key, canonical identifier |
| URL routes (`/patients/{...}`) | `icn` | User-facing, readable |
| CCOW context (`set_context`) | `icn` | CCOW standard uses ICN |
| Display in UI | `icn` | User recognizes ICN format |
| Foreign keys (vitals, allergies) | `patient_key` | Database integrity |

**Current Simplification:**
For Phase 1-8, `patient_key == icn` (same value). The above pattern ensures code remains correct if identity resolution becomes more complex in future phases.

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
# These are READ-ONLY models (med-z4 doesn't modify schema, just inserts data)

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class User(Base):
    """
    User account model (auth.users table).

    This matches the med-z1 auth.users schema exactly.
    med-z4 only READS from this table (doesn't create users).
    """
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    # Primary Key
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Credentials
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)  # bcrypt hash

    # Profile
    display_name = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    home_site_sta3n = Column(Integer)

    # Account Status
    is_active = Column(Boolean, default=True)
    is_locked = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    last_login_at = Column(DateTime)

    # Audit
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), default="system")

    def __repr__(self):
        return f"<User(email={self.email}, display_name={self.display_name})>"


class Session(Base):
    """
    Session model (auth.sessions table).

    med-z4 WRITES to this table when user logs in.
    Sessions are validated by CCOW vault for context operations.
    """
    __tablename__ = "sessions"
    __table_args__ = {"schema": "auth"}

    # Primary Key
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Key to User
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.user_id", ondelete="CASCADE"), nullable=False)

    # Session Lifecycle
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    # Session Status
    is_active = Column(Boolean, default=True)

    # Session Metadata
    ip_address = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(Text)

    def __repr__(self):
        return f"<Session(session_id={self.session_id}, user_id={self.user_id})>"


class AuditLog(Base):
    """
    Audit log model (auth.audit_logs table).

    med-z4 WRITES to this table for authentication events.
    """
    __tablename__ = "audit_logs"
    __table_args__ = {"schema": "auth"}

    # Primary Key
    audit_id = Column(Integer, primary_key=True, autoincrement=True)

    # User (nullable for failed login attempts)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.user_id", ondelete="SET NULL"))

    # Event Information
    event_type = Column(String(50), nullable=False)  # login, logout, login_failed
    event_timestamp = Column(DateTime, default=datetime.utcnow)

    # Event Context
    email = Column(String(255))  # For tracking failed login attempts
    ip_address = Column(String(45))
    user_agent = Column(Text)

    # Event Details
    success = Column(Boolean)
    failure_reason = Column(Text)
    session_id = Column(UUID(as_uuid=True))

    def __repr__(self):
        return f"<AuditLog(event_type={self.event_type}, email={self.email})>"
```

**Learning Note: SQLAlchemy Model Pattern**

- **Base = declarative_base():** All models inherit from this base class
- **__tablename__ and __table_args__:** Map model to specific schema.table
- **Column types:** Match PostgreSQL types exactly (UUID, String, Boolean, etc.)
- **ForeignKey:** Defines relationships (Session.user_id → User.user_id)
- **default=:** Default values for new records (datetime.utcnow, uuid.uuid4)
- **onupdate=:** Automatically update field on record update (updated_at)
- **__repr__:** String representation for debugging (prints in logs, shell)

### 6.4 Authentication Service (app/services/auth_service.py)

Business logic for password verification and session management:

```python
# app/services/auth_service.py
# Authentication business logic for med-z4

import bcrypt
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import update
import logging

from app.models.auth import User, Session as SessionModel, AuditLog
from config import SESSION_TIMEOUT_MINUTES, BCRYPT_ROUNDS

logger = logging.getLogger(__name__)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """
    Verify a plain password against a bcrypt hash.

    Args:
        plain_password: User-provided password (plain text)
        password_hash: Stored bcrypt hash from database

    Returns:
        True if password matches, False otherwise

    Learning Note:
        bcrypt.checkpw() handles the comparison securely.
        It extracts the salt from the hash and recomputes the hash
        with the provided password, then compares in constant time
        to prevent timing attacks.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            password_hash.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Authenticate user by email and password.

    Args:
        db: Database session
        email: User email address
        password: Plain text password

    Returns:
        User object if authentication succeeds, None otherwise

    Side Effects:
        - Updates user.last_login_at on success
        - Updates user.failed_login_attempts on failure
        - Locks account after 5 failed attempts
        - Creates audit log entry
    """
    # Query user by email
    user = db.query(User).filter(User.email == email).first()

    if not user:
        logger.warning(f"Login attempt for non-existent user: {email}")
        _log_failed_login(db, email, "User not found")
        return None

    # Check if account is locked
    if user.is_locked:
        logger.warning(f"Login attempt for locked account: {email}")
        _log_failed_login(db, email, "Account locked")
        return None

    # Check if account is active
    if not user.is_active:
        logger.warning(f"Login attempt for inactive account: {email}")
        _log_failed_login(db, email, "Account inactive")
        return None

    # Verify password
    if not verify_password(password, user.password_hash):
        logger.warning(f"Failed login attempt for {email}: Invalid password")

        # Increment failed login attempts
        user.failed_login_attempts += 1

        # Lock account after 5 failed attempts
        if user.failed_login_attempts >= 5:
            user.is_locked = True
            logger.warning(f"Account locked after 5 failed attempts: {email}")

        db.commit()
        _log_failed_login(db, email, "Invalid password")
        return None

    # Authentication successful
    logger.info(f"Successful login: {email}")

    # Reset failed login attempts
    user.failed_login_attempts = 0
    user.last_login_at = datetime.utcnow()
    db.commit()

    return user


def create_session(
    db: Session,
    user: User,
    ip_address: str,
    user_agent: str
) -> Dict[str, Any]:
    """
    Create a new session for authenticated user.

    Args:
        db: Database session
        user: Authenticated user object
        ip_address: Client IP address
        user_agent: Client user agent string

    Returns:
        Dictionary with session info:
        {
            "session_id": str,
            "user_id": str,
            "expires_at": datetime
        }

    Side Effects:
        - Inserts new row into auth.sessions table
        - Creates audit log entry
    """
    # Generate session ID
    session_id = uuid.uuid4()

    # Calculate expiration time
    expires_at = datetime.utcnow() + timedelta(minutes=SESSION_TIMEOUT_MINUTES)

    # Create session record
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
    db.commit()

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
    db.commit()

    logger.info(f"Session created for {user.email}: {session_id}")

    return {
        "session_id": str(session_id),
        "user_id": str(user.user_id),
        "expires_at": expires_at,
    }


def invalidate_session(db: Session, session_id: str) -> bool:
    """
    Invalidate (logout) a session.

    Args:
        db: Database session
        session_id: Session UUID to invalidate

    Returns:
        True if session was invalidated, False if not found

    Side Effects:
        - Sets auth.sessions.is_active = False
        - Creates audit log entry
    """
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        logger.warning(f"Invalid session ID format: {session_id}")
        return False

    # Update session to inactive
    result = db.execute(
        update(SessionModel)
        .where(SessionModel.session_id == session_uuid)
        .values(is_active=False)
    )
    db.commit()

    if result.rowcount > 0:
        logger.info(f"Session invalidated: {session_id}")

        # Log logout event
        session = db.query(SessionModel).filter(
            SessionModel.session_id == session_uuid
        ).first()

        if session:
            audit_log = AuditLog(
                user_id=session.user_id,
                event_type="logout",
                event_timestamp=datetime.utcnow(),
                success=True,
                session_id=session_uuid,
            )
            db.add(audit_log)
            db.commit()

        return True

    return False


def _log_failed_login(db: Session, email: str, reason: str):
    """
    Internal helper to log failed login attempts.

    Args:
        db: Database session
        email: Email address attempted
        reason: Failure reason (for audit trail)
    """
    audit_log = AuditLog(
        user_id=None,  # No user_id for failed attempts
        event_type="login_failed",
        event_timestamp=datetime.utcnow(),
        email=email,
        success=False,
        failure_reason=reason,
    )
    db.add(audit_log)
    db.commit()
```

**Learning Note: Authentication Security Patterns**

1. **Password Hashing (bcrypt):**
   - Never store passwords in plaintext
   - bcrypt includes salt automatically (no separate salt column needed)
   - bcrypt is intentionally slow (~300ms) to resist brute-force attacks
   - Cost factor (BCRYPT_ROUNDS=12) determines slowness (higher = more secure, slower)

2. **Account Locking:**
   - Prevents brute-force password guessing
   - Locks account after 5 failed attempts
   - Production systems: Add unlock mechanism (email reset link, admin unlock)

3. **Audit Logging:**
   - Log all authentication events (success, failure, logout)
   - Captures email, IP, user agent for forensics
   - HIPAA compliance requires audit trails for PHI access

4. **Session Expiration:**
   - Sessions expire after inactivity timeout (25 minutes)
   - Forces re-authentication for security
   - Production: Implement session renewal on activity

### 6.5 Login Route (app/routes/auth.py)

FastAPI endpoints for login, logout, and session management:

```python
# app/routes/auth.py
# Authentication routes for med-z4

from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from app.services.auth_service import authenticate_user, create_session, invalidate_session
from config import SESSION_COOKIE_NAME, SESSION_COOKIE_MAX_AGE

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    Display login form.

    GET /login

    Returns:
        HTML login page with email and password inputs
    """
    return templates.TemplateResponse("login.html", {
        "request": request,
    })


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Process login form submission.

    POST /login

    Form Data:
        email: User email address
        password: User password (plain text, HTTPS required in production)

    Returns:
        Redirect to /dashboard on success
        Redirect to /login with error on failure

    Side Effects:
        - Sets session cookie (med_z4_session_id) on success
        - Creates session in auth.sessions table
        - Updates user.last_login_at
        - Creates audit log entry
    """
    # Get client IP and user agent
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent", "unknown")

    # Authenticate user
    user = authenticate_user(db, email, password)

    if not user:
        # Authentication failed - return to login with error
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid email or password. Please try again.",
        }, status_code=status.HTTP_401_UNAUTHORIZED)

    # Create session
    session_info = create_session(db, user, ip_address, user_agent)

    # Set session cookie and redirect to dashboard
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_info["session_id"],
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,  # Prevents JavaScript access (XSS protection)
        samesite="lax",  # CSRF protection
        secure=False,  # Set to True in production (requires HTTPS)
    )

    return response


@router.post("/logout")
async def logout(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Logout user by invalidating session.

    POST /logout

    Returns:
        Redirect to /login

    Side Effects:
        - Deletes session cookie
        - Marks session as inactive in database
        - Creates audit log entry
    """
    # Get session ID from cookie
    session_id = request.cookies.get(SESSION_COOKIE_NAME)

    if session_id:
        # Invalidate session in database
        invalidate_session(db, session_id)

    # Delete cookie and redirect to login
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key=SESSION_COOKIE_NAME)

    return response
```

**Learning Note: FastAPI Form Handling**

- **Form(...)**  Extracts form field from POST request body (application/x-www-form-urlencoded)
- **Depends(get_db):** FastAPI dependency injection - provides database session
- **RedirectResponse:** HTTP 303 See Other redirect (POST-Redirect-GET pattern)
- **response.set_cookie():** Sets HTTP-only session cookie
- **httponly=True:** Prevents JavaScript from accessing cookie (XSS defense)
- **samesite="lax":** Prevents CSRF attacks (cookie not sent on cross-site requests)

### 6.6 Login UI Template (templates/login.html)

Jinja2 template for login page with Teal theme:

```html
{# templates/login.html #}
{# Login page for med-z4 with password authentication #}

{% extends "base.html" %}

{% block title %}Login - med-z4 EHR{% endblock %}

{% block content %}
<div class="login-container">
    <div class="login-card">
        {# Logo and Title #}
        <div class="login-header">
            <img src="/static/images/logo-teal.png" alt="med-z4 Logo" class="login-logo">
            <h1>med-z4 Simple EHR</h1>
            <p class="login-subtitle">Patient Context Management & Clinical Data Entry</p>
        </div>

        {# Error Message #}
        {% if error %}
        <div class="alert alert-error">
            <strong>Login Failed:</strong> {{ error }}
        </div>
        {% endif %}

        {# Login Form #}
        <form method="POST" action="/login" class="login-form">
            <div class="form-group">
                <label for="email">Email Address</label>
                <input
                    type="email"
                    id="email"
                    name="email"
                    required
                    autofocus
                    placeholder="clinician.alpha@va.gov"
                    class="form-control"
                >
            </div>

            <div class="form-group">
                <label for="password">Password</label>
                <input
                    type="password"
                    id="password"
                    name="password"
                    required
                    placeholder="Enter your password"
                    class="form-control"
                >
            </div>

            <button type="submit" class="btn btn-primary btn-block">
                Sign In to med-z4
            </button>
        </form>

        {# Helpful Hint (Like med-z1) #}
        <div class="login-hint">
            <p><strong>Test Credentials:</strong></p>
            <p>Email: <code>clinician.alpha@va.gov</code></p>
            <p>Password: <code>VaDemo2025!</code></p>
            <p class="hint-note">
                Note: med-z4 uses the same user database as med-z1,
                but requires separate login for independent session management.
            </p>
        </div>
    </div>
</div>
{% endblock %}
```

**Learning Note: Jinja2 Template Syntax**

- **{% extends "base.html" %}:** Template inheritance (base provides layout)
- **{% block title %}...{% endblock %}:** Override block from base template
- **{{ error }}:** Variable substitution (escaped by default for XSS protection)
- **{% if error %}...{% endif %}:** Conditional rendering
- **{# Comment #}:** Template comments (not included in rendered HTML)
- **method="POST" action="/login":** Form submits to POST /login route

### 6.7 Session Validation Middleware

med-z4 validates sessions for protected routes using a FastAPI dependency:

```python
# app/middleware/auth.py
# Session validation middleware for protected routes

from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any

from database import get_db
from app.models.auth import Session as SessionModel, User
from config import SESSION_COOKIE_NAME
import logging
import uuid

logger = logging.getLogger(__name__)


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    FastAPI dependency to validate session and extract current user.

    This function:
    1. Extracts session_id from cookie
    2. Validates session exists and is active
    3. Checks session has not expired
    4. Returns user information

    Usage in routes:
        @router.get("/dashboard")
        async def dashboard(user: Dict = Depends(get_current_user)):
            return {"message": f"Welcome {user['display_name']}"}

    Raises:
        HTTPException(401) if session is invalid or expired
        HTTPException(302) redirects to /login if not authenticated

    Returns:
        Dictionary with user info:
        {
            "user_id": str,
            "email": str,
            "display_name": str,
            "session_id": str
        }
    """
    # Extract session ID from cookie
    session_id = request.cookies.get(SESSION_COOKIE_NAME)

    if not session_id:
        logger.warning("No session cookie found")
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"}
        )

    # Parse session UUID
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        logger.warning(f"Invalid session ID format: {session_id}")
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"}
        )

    # Query session with joined user
    session = db.query(SessionModel).filter(
        SessionModel.session_id == session_uuid
    ).first()

    if not session:
        logger.warning(f"Session not found: {session_id}")
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"}
        )

    # Validate session is active
    if not session.is_active:
        logger.warning(f"Session is inactive: {session_id}")
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"}
        )

    # Validate session has not expired
    if session.expires_at < datetime.utcnow():
        logger.warning(f"Session expired: {session_id}")
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"}
        )

    # Get user information
    user = db.query(User).filter(User.user_id == session.user_id).first()

    if not user or not user.is_active:
        logger.warning(f"User not found or inactive for session: {session_id}")
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"}
        )

    # Return user info
    return {
        "user_id": str(user.user_id),
        "email": user.email,
        "display_name": user.display_name,
        "session_id": session_id,
    }
```

**Learning Note: FastAPI Dependency Injection**

- **Depends(get_current_user):** FastAPI will call this function before route handler
- **Automatic validation:** If dependency raises HTTPException, route handler never runs
- **Reusable:** Same dependency used across all protected routes
- **Type-safe:** Return type (Dict[str, Any]) provides autocomplete in IDEs
- **Testable:** Dependencies can be overridden in tests

**Example Usage in Routes:**

```python
from app.middleware.auth import get_current_user

@router.get("/dashboard")
async def dashboard(
    request: Request,
    user: Dict = Depends(get_current_user)
):
    # user is automatically validated and populated
    # If invalid, user never reaches this point (redirected to /login)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
    })
```

---

- `user_login` - Successful login
- `user_logout` - Explicit logout
- `session_expired` - Session timeout
- `login_failed` - Failed login attempt

**Extended Scope for med-z4:**

To support HIPAA compliance and security audit requirements, med-z4 should log clinical data access events.

**Option 1: Reuse auth.audit_logs (Recommended for Phase 1-8)**

Extend `event_type` values to include clinical events:

```python
# Clinical access events
'patient_view'       # Viewed patient detail page
'patient_create'     # Created new patient
'patient_update'     # Edited patient demographics
'patient_delete'     # Deleted patient (if implemented)
'vital_create'       # Added vital signs
'vital_update'       # Edited vital signs
'vital_delete'       # Deleted vital signs
'allergy_create'     # Added allergy
'allergy_delete'     # Deleted allergy
'note_create'        # Created clinical note
'note_view'          # Viewed full clinical note
'note_delete'        # Deleted clinical note
'ccow_set'           # Set CCOW context
'ccow_clear'         # Cleared CCOW context
```

**Example Audit Log Function:**

```python
# app/services/audit_service.py
from datetime import datetime
from sqlalchemy import insert
from app.models.auth import AuditLog

async def log_clinical_event(
    db: AsyncSession,
    user_id: int,
    event_type: str,
    patient_icn: str | None = None,
    resource_id: int | None = None,
    details: str | None = None
):
    """
    Log clinical data access event for HIPAA compliance.

    Args:
        user_id: ID of user performing action
        event_type: Event type (e.g., 'patient_view', 'vital_create')
        patient_icn: ICN of patient being accessed (if applicable)
        resource_id: ID of specific resource (vital_id, allergy_id, etc.)
        details: Additional context (e.g., "Viewed patient demographics")
    """
    await db.execute(
        insert(AuditLog).values(
            user_id=user_id,
            event_type=event_type,
            event_timestamp=datetime.utcnow(),
            ip_address=None,  # Can get from request if needed
            user_agent=None,
            details=f"Patient: {patient_icn}, Resource: {resource_id}, {details}" if patient_icn else details
        )
    )
    await db.commit()
```

**Usage in Routes:**

```python
@router.get("/patients/{icn}")
async def patient_detail(
    icn: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Display patient detail page"""
    # ... fetch patient data ...

    # Audit log the access
    await log_clinical_event(
        db=db,
        user_id=current_user.user_id,
        event_type='patient_view',
        patient_icn=icn,
        details="Viewed patient demographics and clinical data"
    )

    return templates.TemplateResponse("patient_detail.html", {...})
```

**Option 2: Separate clinical.audit_access Table (Future Production)**

For higher-volume production systems, create dedicated audit table:

```sql
CREATE TABLE clinical.audit_access (
    audit_id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth.users(user_id),
    event_type VARCHAR(50) NOT NULL,
    event_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    patient_key VARCHAR(50),  -- ICN of patient accessed
    resource_type VARCHAR(50),  -- 'vital', 'allergy', 'note', etc.
    resource_id INTEGER,  -- Specific vital_id, allergy_id, etc.
    action VARCHAR(20),  -- 'view', 'create', 'update', 'delete'
    ip_address VARCHAR(45),
    user_agent TEXT,
    details TEXT
);

CREATE INDEX idx_audit_access_patient ON clinical.audit_access(patient_key, event_timestamp);
CREATE INDEX idx_audit_access_user ON clinical.audit_access(user_id, event_timestamp);
```

**Phase 1-8 Recommendation:**
- Use Option 1 (reuse `auth.audit_logs`) for simplicity
- Log at minimum: `patient_view`, `patient_create`, `vital_create`, `allergy_create`, `note_create`
- Add `note_view` for full note access (sensitive narrative text)
- Defer comprehensive audit logging to production hardening phase

**Audit Log Retention:**
- Development: 30 days (configurable, can truncate older logs)
- Production: 7 years (HIPAA requirement for audit trail retention)

---


---

# med-z4 Design Specification - Section 3
# CCOW Integration & Core Features

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

**Key Endpoints:**

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/ccow/health` | Health check | No |
| GET | `/ccow/active-patient` | Get current user's active patient | Yes (session cookie) |
| PUT | `/ccow/active-patient` | Set current user's active patient | Yes (session cookie) |
| DELETE | `/ccow/active-patient` | Clear current user's active patient | Yes (session cookie) |
| GET | `/ccow/history?scope=user\|global` | Get context change history | Yes (session cookie) |
| GET | `/ccow/active-patients` | Get all users' contexts (admin) | Yes (session cookie) |

**Authentication:**

- All endpoints (except `/ccow/health`) require `session_id` cookie
- Vault validates cookie against `auth.sessions` table
- Extracts `user_id` from validated session (not from request body)
- Context operations are scoped to authenticated user

**Security Model:**

- User cannot spoof `user_id` (extracted from session, not request)
- User can only read/write their own context
- Admin endpoints (`/active-patients`) return all contexts (for debugging)

### 7.3 CCOW Client (app/services/ccow_client.py)

HTTP client for communicating with CCOW Context Vault:

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

    This client handles all HTTP communication with the CCOW vault.
    It automatically includes the session cookie for authentication.

    Usage:
        client = CCOWClient(session_id="user-session-uuid")
        context = client.get_context()
        client.set_context("ICN100001")
    """

    def __init__(self, session_id: str):
        """
        Initialize CCOW client with session ID.

        Args:
            session_id: User's session UUID (from cookie)
        """
        self.base_url = CCOW_BASE_URL
        self.session_id = session_id
        self.cookies = {SESSION_COOKIE_NAME: session_id}  # CCOW expects 'session_id' cookie

    def get_context(self) -> Optional[Dict[str, Any]]:
        """
        Get current user's active patient context from vault.

        Returns:
            Dictionary with context info if context exists:
            {
                "user_id": str,
                "email": str,
                "patient_id": str (ICN),
                "set_by": str (application name),
                "set_at": str (ISO timestamp),
                "last_accessed_at": str (ISO timestamp)
            }
            Returns None if no context exists (404) or error occurs.

        HTTP Status Codes:
            200: Context found
            404: No active context for user
            401: Session invalid or expired
        """
        try:
            response = httpx.get(
                f"{self.base_url}/ccow/active-patient",
                cookies=self.cookies,
                timeout=5.0,
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                # No context exists (not an error)
                return None
            elif response.status_code == 401:
                logger.warning("CCOW vault rejected session (401 Unauthorized)")
                return None
            else:
                logger.error(f"CCOW get_context error: {response.status_code} {response.text}")
                return None

        except httpx.RequestError as e:
            logger.error(f"CCOW vault connection error: {e}")
            return None

    def set_context(self, patient_id: str, set_by: str = "med-z4") -> bool:
        """
        Set current user's active patient context in vault.

        Args:
            patient_id: Patient ICN (e.g., "ICN100001")
            set_by: Application name (default: "med-z4")

        Returns:
            True if context was set successfully, False otherwise

        HTTP Status Codes:
            200: Context set successfully
            401: Session invalid or expired
            400: Invalid request (missing patient_id)
        """
        try:
            response = httpx.put(
                f"{self.base_url}/ccow/active-patient",
                json={"patient_id": patient_id, "set_by": set_by},
                cookies=self.cookies,
                timeout=5.0,
            )

            if response.status_code == 200:
                logger.info(f"CCOW context set: {patient_id} by {set_by}")
                return True
            elif response.status_code == 401:
                logger.warning("CCOW vault rejected session (401 Unauthorized)")
                return False
            else:
                logger.error(f"CCOW set_context error: {response.status_code} {response.text}")
                return False

        except httpx.RequestError as e:
            logger.error(f"CCOW vault connection error: {e}")
            return False

    def clear_context(self, cleared_by: str = "med-z4") -> bool:
        """
        Clear current user's active patient context in vault.

        Args:
            cleared_by: Application name (default: "med-z4")

        Returns:
            True if context was cleared, False otherwise

        HTTP Status Codes:
            204: Context cleared successfully
            404: No context to clear (not an error for this operation)
            401: Session invalid or expired
        """
        try:
            response = httpx.delete(
                f"{self.base_url}/ccow/active-patient",
                json={"cleared_by": cleared_by},
                cookies=self.cookies,
                timeout=5.0,
            )

            if response.status_code in (204, 404):
                logger.info("CCOW context cleared")
                return True
            elif response.status_code == 401:
                logger.warning("CCOW vault rejected session (401 Unauthorized)")
                return False
            else:
                logger.error(f"CCOW clear_context error: {response.status_code}")
                return False

        except httpx.RequestError as e:
            logger.error(f"CCOW vault connection error: {e}")
            return False

    def get_history(self, scope: str = "user") -> Optional[Dict[str, Any]]:
        """
        Get context change history from vault.

        Args:
            scope: "user" (only current user's events) or "global" (all users)

        Returns:
            Dictionary with history:
            {
                "history": List[Dict],  # List of context change events
                "scope": str,           # "user" or "global"
                "total_count": int,
                "user_id": str (if scope="user")
            }
            Returns None if error occurs.
        """
        try:
            response = httpx.get(
                f"{self.base_url}/ccow/history",
                params={"scope": scope},
                cookies=self.cookies,
                timeout=5.0,
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                logger.warning("CCOW vault rejected session (401 Unauthorized)")
                return None
            else:
                logger.error(f"CCOW get_history error: {response.status_code}")
                return None

        except httpx.RequestError as e:
            logger.error(f"CCOW vault connection error: {e}")
            return None

    def health_check(self) -> bool:
        """
        Check if CCOW vault is reachable and healthy.

        Returns:
            True if vault is healthy, False otherwise

        Note:
            This endpoint does not require authentication.
        """
        try:
            response = httpx.get(
                f"{self.base_url}/ccow/health",
                timeout=5.0,
            )
            return response.status_code == 200
        except httpx.RequestError:
            return False
```

**Learning Note: HTTP Client Patterns**

- **httpx:** Modern async HTTP client (similar to requests, but supports async)
- **timeout=5.0:** Prevents hanging requests (5 second timeout)
- **cookies=:** Automatically includes session cookie in every request
- **response.status_code:** HTTP status code (200=success, 404=not found, 401=unauthorized)
- **response.json():** Parse JSON response body
- **try/except RequestError:** Catches network errors (vault not running, DNS failure, etc.)

### 7.4 CCOW Context Routes (app/routes/context.py)

FastAPI routes for CCOW context operations:

```python
# app/routes/context.py
# CCOW context management routes for med-z4

from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any

from app.middleware.auth import get_current_user
from app.services.ccow_client import CCOWClient
import logging

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


@router.post("/context/set/{patient_icn}")
async def set_context(
    patient_icn: str,
    user: Dict = Depends(get_current_user)
):
    """
    Set active patient context in CCOW vault.

    POST /context/set/{patient_icn}

    Args:
        patient_icn: Patient ICN from URL path (e.g., "ICN100001")
        user: Current authenticated user (from session)

    Returns:
        JSON response:
        {
            "success": true,
            "patient_id": "ICN100001",
            "message": "Context set successfully"
        }

    Raises:
        500: If CCOW vault communication fails

    Usage:
        Called by HTMX when user clicks "Select" button in patient roster.
        Response triggers HTMX to update active patient banner (OOB swap).
    """
    # Create CCOW client with user's session
    ccow = CCOWClient(session_id=user["session_id"])

    # Set context in vault
    success = ccow.set_context(patient_icn, set_by="med-z4")

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to communicate with CCOW vault"
        )

    return JSONResponse({
        "success": True,
        "patient_id": patient_icn,
        "message": "Context set successfully"
    })


@router.delete("/context/clear")
async def clear_context(
    user: Dict = Depends(get_current_user)
):
    """
    Clear active patient context in CCOW vault.

    DELETE /context/clear

    Returns:
        JSON response:
        {
            "success": true,
            "message": "Context cleared"
        }

    Usage:
        Called by HTMX when user clicks "Clear Context" button.
    """
    # Create CCOW client with user's session
    ccow = CCOWClient(session_id=user["session_id"])

    # Clear context in vault
    success = ccow.clear_context(cleared_by="med-z4")

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to communicate with CCOW vault"
        )

    return JSONResponse({
        "success": True,
        "message": "Context cleared"
    })


@router.get("/context/active", response_class=HTMLResponse)
async def get_active_context_banner(
    request: Request,
    user: Dict = Depends(get_current_user)
):
    """
    Get active patient banner (HTMX partial).

    GET /context/active

    Returns:
        HTML fragment showing active patient or "No Context"

    Usage:
        Called by HTMX polling (every 5 seconds) to detect context changes.
        Renders templates/partials/active_patient_banner.html
    """
    # Create CCOW client with user's session
    ccow = CCOWClient(session_id=user["session_id"])

    # Get current context from vault
    context = ccow.get_context()

    return templates.TemplateResponse("partials/active_patient_banner.html", {
        "request": request,
        "context": context,  # None if no context, Dict if context exists
        "user": user,
    })


@router.get("/context/debug", response_class=HTMLResponse)
async def get_ccow_debug_panel(
    request: Request,
    user: Dict = Depends(get_current_user)
):
    """
    Get CCOW debug panel (HTMX partial).

    GET /context/debug

    Returns:
        HTML fragment showing CCOW status, context ID, last sync time

    Usage:
        Called by HTMX polling (every 5 seconds) for debug widget.
        Renders templates/partials/ccow_debug_panel.html
    """
    # Create CCOW client with user's session
    ccow = CCOWClient(session_id=user["session_id"])

    # Get context and health status
    context = ccow.get_context()
    vault_healthy = ccow.health_check()

    return templates.TemplateResponse("partials/ccow_debug_panel.html", {
        "request": request,
        "context": context,
        "vault_healthy": vault_healthy,
        "user": user,
    })
```

**Learning Note: HTMX Integration Patterns**

- **HTMX Polling:** Browser automatically calls `/context/active` every 5 seconds
- **Partial Templates:** Routes return HTML fragments, not full pages
- **Out-of-Band (OOB) Swaps:** HTMX can update multiple page elements from single response
- **Path Parameters:** `{patient_icn}` extracts value from URL (e.g., `/context/set/ICN100001`)

---

### 7.5 Session Cookie Contract with CCOW Vault

**Problem Statement:**
med-z4 uses a different session cookie name (`med_z4_session_id`) than med-z1 (`session_id`) to enable independent login sessions. The CCOW Vault must be able to validate sessions from both applications.

**CCOW Vault Implementation (Current v2.0):**

The CCOW Vault uses **cookie-name-agnostic session validation**:

1. **Vault reads ALL cookies** from incoming requests
2. **Searches for UUID-format values** in any cookie
3. **Validates each UUID** against `auth.sessions` table:
   ```python
   # ccow/auth_helper.py
   def get_user_from_session(session_id: str) -> Optional[Dict[str, Any]]:
       """
       Validates session_id (UUID) against auth.sessions table.
       Does NOT care about cookie name - only validates the UUID value.
       """
       result = db.execute(
           "SELECT u.user_id, u.username, u.email, u.role "
           "FROM auth.users u "
           "JOIN auth.sessions s ON s.user_id = u.user_id "
           "WHERE s.session_id = %s AND s.is_active = TRUE "
           "AND s.expires_at > NOW()",
           (session_id,)
       )
       return result.fetchone() if result else None
   ```

4. **First valid session wins** (order: `session_id`, then `med_z4_session_id`, then other cookies)

**Why This Works:**
- med-z1 sends cookie: `session_id=<uuid-1>`
- med-z4 sends cookie: `med_z4_session_id=<uuid-2>`
- Vault validates both by checking UUID against `auth.sessions`
- Separate cookie names prevent session collision

**Developer Implementation Guidance:**

When making CCOW API calls from med-z4:

```python
# app/services/ccow_client.py
import httpx
from fastapi import Request

class CCOWClient:
    def __init__(self, session_id: str):
        """
        session_id: The UUID value from med_z4_session_id cookie
        """
        self.base_url = "http://localhost:8001"
        # Send session as med_z4_session_id cookie
        self.cookies = {"med_z4_session_id": session_id}

    async def set_context(self, patient_icn: str) -> Dict[str, Any]:
        """Set CCOW active patient context"""
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/ccow/active-patient",
                json={"icn": patient_icn},
                cookies=self.cookies,  # Vault validates this UUID
                timeout=5.0
            )
            response.raise_for_status()
            return response.json()
```

**Verification Test:**

1. Log into med-z1 with user `alice` (creates `session_id=<uuid-1>`)
2. Log into med-z4 with user `bob` (creates `med_z4_session_id=<uuid-2>`)
3. med-z4: Set context to patient ICN100001
4. Check CCOW Vault history: Should show `bob` (not `alice`) set the context
5. med-z1: Active patient should update to ICN100001

**Contract Summary:**
- **Cookie Name:** Applications can use ANY cookie name (med-z4 uses `med_z4_session_id`)
- **Cookie Value:** Must be a valid UUID that exists in `auth.sessions` table
- **Vault Behavior:** Validates UUID value against database, ignores cookie name
- **Multi-User Support:** Different users in med-z1 and med-z4 can set context independently

---

## 8. Core Features (Phase 1-5)

### 8.1 Feature: Patient Roster (Dashboard)

**Purpose:** Display list of all patients from `clinical.patient_demographics` with "Select" action.

**Route:** `GET /dashboard`

**UI Components:**
- Table with columns: Name, ICN, DOB, Sex, Age
- "Select" button for each patient (sets CCOW context)
- Search/filter bar (optional, Phase 5)
- Active patient banner at top (shows current context)

**Database Query:**

```python
# app/routes/dashboard.py
# Dashboard route with patient roster

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Dict

from database import get_db
from app.middleware.auth import get_current_user
from app.models.clinical import PatientDemographics  # To be defined in Section 4
from app.services.ccow_client import CCOWClient

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Display patient roster dashboard.

    GET /dashboard

    Returns:
        HTML page with patient table and active context banner

    Query:
        Loads all patients from clinical.patient_demographics
        Orders by name_last, name_first
    """
    # Get all patients
    patients = db.query(PatientDemographics).order_by(
        PatientDemographics.name_last,
        PatientDemographics.name_first
    ).all()

    # Get current CCOW context
    ccow = CCOWClient(session_id=user["session_id"])
    context = ccow.get_context()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "patients": patients,
        "context": context,
    })
```

**Template (templates/dashboard.html):**

```html
{# templates/dashboard.html #}
{# Patient roster dashboard for med-z4 #}

{% extends "base.html" %}

{% block title %}Patient Roster - med-z4{% endblock %}

{% block content %}
{# Active Patient Banner (HTMX polling target) #}
<div
    id="active-patient-banner"
    hx-get="/context/active"
    hx-trigger="load, every 5s"
    hx-swap="outerHTML"
>
    {# Initial content (will be replaced by HTMX) #}
    {% include "partials/active_patient_banner.html" %}
</div>

{# Patient Roster Table #}
<div class="dashboard-container">
    <div class="dashboard-header">
        <h1>Patient Roster</h1>
        <p>{{ patients|length }} patients</p>
    </div>

    <table class="patient-table">
        <thead>
            <tr>
                <th>Name</th>
                <th>ICN</th>
                <th>DOB</th>
                <th>Sex</th>
                <th>Age</th>
                <th>Action</th>
            </tr>
        </thead>
        <tbody>
            {% for patient in patients %}
            <tr class="{% if context and context.patient_id == patient.icn %}active-context{% endif %}">
                <td>{{ patient.name_display }}</td>
                <td><code>{{ patient.icn }}</code></td>
                <td>{{ patient.dob.strftime('%Y-%m-%d') if patient.dob else 'N/A' }}</td>
                <td>{{ patient.sex or 'N/A' }}</td>
                <td>{{ patient.age or 'N/A' }}</td>
                <td>
                    <button
                        class="btn btn-sm btn-primary"
                        hx-post="/context/set/{{ patient.icn }}"
                        hx-target="#active-patient-banner"
                        hx-swap="outerHTML"
                    >
                        Select
                    </button>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

{# CCOW Debug Panel (optional, bottom-right corner) #}
<div
    id="ccow-debug-panel"
    hx-get="/context/debug"
    hx-trigger="load, every 5s"
    hx-swap="outerHTML"
>
    {% include "partials/ccow_debug_panel.html" %}
</div>
{% endblock %}
```

**Learning Note: HTMX Attributes**

- **hx-get="/context/active":** Makes GET request to /context/active
- **hx-trigger="load, every 5s":** Trigger on page load, then every 5 seconds
- **hx-swap="outerHTML":** Replace entire element with response HTML
- **hx-post="/context/set/{{ patient.icn }}":** POST to set context endpoint
- **hx-target="#active-patient-banner":** Update element with ID (not the button itself)

### 8.2 Feature: Active Patient Banner

**Purpose:** Display currently active patient from CCOW context at top of page.

**Template (templates/partials/active_patient_banner.html):**

```html
{# templates/partials/active_patient_banner.html #}
{# Active patient context banner (HTMX partial) #}

<div id="active-patient-banner" class="active-patient-banner">
    {% if context and context.patient_id %}
        {# Context exists - show patient info #}
        <div class="banner-content active">
            <span class="banner-label">ACTIVE CONTEXT:</span>
            <span class="banner-patient">
                <strong>{{ context.patient_id }}</strong>
            </span>
            <span class="banner-source">(Set by {{ context.set_by }})</span>
            <button
                class="btn btn-sm btn-danger"
                hx-delete="/context/clear"
                hx-target="#active-patient-banner"
                hx-swap="outerHTML"
            >
                Clear Context
            </button>
        </div>
    {% else %}
        {# No context - show empty state #}
        <div class="banner-content empty">
            <span class="banner-label">NO ACTIVE CONTEXT</span>
            <span class="banner-hint">Select a patient from the roster below</span>
        </div>
    {% endif %}
</div>
```

**CSS (static/css/style.css - Teal Theme):**

```css
/* Active Patient Banner */
.active-patient-banner {
    position: sticky;
    top: 0;
    z-index: 100;
    background: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%);  /* Teal gradient */
    color: white;
    padding: 1rem 2rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.banner-content {
    display: flex;
    align-items: center;
    gap: 1rem;
    font-size: 1.1rem;
}

.banner-content.active {
    justify-content: space-between;
}

.banner-content.empty {
    justify-content: center;
    opacity: 0.8;
}

.banner-label {
    font-weight: 600;
    font-size: 0.9rem;
    letter-spacing: 0.05em;
}

.banner-patient {
    font-size: 1.2rem;
}

.banner-source {
    font-size: 0.9rem;
    opacity: 0.9;
}
```

### 8.3 Feature: CCOW Debug Panel

**Purpose:** Show CCOW vault status and context details for debugging.

**Template (templates/partials/ccow_debug_panel.html):**

```html
{# templates/partials/ccow_debug_panel.html #}
{# CCOW debug panel (optional, bottom-right corner) #}

<div id="ccow-debug-panel" class="ccow-debug-panel">
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
            {% if context %}
                {{ context.patient_id[:15] }}...
            {% else %}
                None
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

**CSS:**

```css
/* CCOW Debug Panel */
.ccow-debug-panel {
    position: fixed;
    bottom: 1rem;
    right: 1rem;
    background: white;
    border: 2px solid #14b8a6;  /* Teal border */
    border-radius: 8px;
    padding: 1rem;
    font-size: 0.875rem;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    min-width: 250px;
}

.debug-header {
    font-weight: 600;
    color: #14b8a6;  /* Teal */
    margin-bottom: 0.75rem;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 0.5rem;
}

.debug-row {
    display: flex;
    justify-content: space-between;
    padding: 0.25rem 0;
}

.debug-label {
    color: #6b7280;
    font-weight: 500;
}

.debug-value {
    color: #111827;
    font-family: 'Courier New', monospace;
}

.status-indicator {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 0.25rem;
}

.status-indicator.online {
    background-color: #10b981;  /* Green */
}

.status-indicator.offline {
    background-color: #ef4444;  /* Red */
}
```

### 8.4 UI Theme: Teal/Emerald Distinction

**Color Palette (med-z4):**

```css
/* med-z4 Teal Theme */
:root {
    /* Primary Colors (Teal/Emerald) */
    --primary-50: #f0fdfa;
    --primary-100: #ccfbf1;
    --primary-200: #99f6e4;
    --primary-300: #5eead4;
    --primary-400: #2dd4bf;
    --primary-500: #14b8a6;  /* Main brand color */
    --primary-600: #0d9488;
    --primary-700: #0f766e;
    --primary-800: #115e59;
    --primary-900: #134e4a;

    /* Contrast with med-z1 Blue Theme */
    /* med-z1 uses #3b82f6 (blue-500) */
    /* med-z4 uses #14b8a6 (teal-500) */
}

/* Apply Teal theme to buttons */
.btn-primary {
    background-color: var(--primary-500);
    border-color: var(--primary-600);
}

.btn-primary:hover {
    background-color: var(--primary-600);
}

/* Navigation bar */
.topbar {
    background-color: var(--primary-600);
}
```

**Visual Comparison:**

| Element | med-z1 (Blue) | med-z4 (Teal) |
|---------|---------------|---------------|
| Primary Color | #3b82f6 (Blue) | #14b8a6 (Teal) |
| Header | Dark Blue | Dark Teal |
| Buttons | Blue | Teal |
| Logo | Blue Badge | Teal Badge |
| Accent | Slate | Emerald |
# med-z4 Design Specification - Section 4
# CRUD Features & Implementation Roadmap

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

**ICN Generator Utility (app/services/patient_service.py):**

```python
# app/services/patient_service.py
# Patient data management service for med-z4

import random
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from app.models.clinical import PatientDemographics


def generate_test_icn() -> str:
    """
    Generate a unique test ICN in 999 series.

    Format: 999V######
    Example: 999V123456

    Returns:
        ICN string in 999 series
    """
    suffix = random.randint(100000, 999999)
    return f"999V{suffix}"


def icn_exists(db: Session, icn: str) -> bool:
    """
    Check if ICN already exists in database.

    Args:
        db: Database session
        icn: ICN to check

    Returns:
        True if ICN exists, False otherwise
    """
    return db.query(PatientDemographics).filter(
        PatientDemographics.icn == icn
    ).count() > 0


def generate_unique_icn(db: Session) -> str:
    """
    Generate a unique test ICN (guaranteed not to exist).

    Args:
        db: Database session

    Returns:
        Unique ICN string

    Note:
        Loops until unique ICN is found (max 10 attempts).
        Raises ValueError if unable to generate unique ICN.
    """
    for attempt in range(10):
        icn = generate_test_icn()
        if not icn_exists(db, icn):
            return icn

    raise ValueError("Unable to generate unique ICN after 10 attempts")
```

### 9.3 Clinical Data Models (app/models/clinical.py)

SQLAlchemy models matching med-z1 PostgreSQL schema:

```python
# app/models/clinical.py
# Clinical data models for med-z4 (matches med-z1 serving database schema)

from datetime import datetime, date
from typing import Optional
from sqlalchemy import Column, String, Integer, Date, DateTime, Text, DECIMAL, Boolean, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class PatientDemographics(Base):
    """
    Patient demographics model (clinical.patient_demographics table).

    This matches the med-z1 schema exactly (see postgresql-database-reference.md).
    med-z4 both READS (roster display) and WRITES (create new patients).
    """
    __tablename__ = "patient_demographics"
    __table_args__ = {"schema": "clinical"}

    # Primary Key and Identity
    patient_key = Column(String(50), primary_key=True)  # Same as ICN for med-z1
    icn = Column(String(50), unique=True, nullable=False)

    # Core Demographics
    ssn = Column(String(64))  # Encrypted in production
    ssn_last4 = Column(String(4))
    name_last = Column(String(100))
    name_first = Column(String(100))
    name_display = Column(String(200))  # "LAST, First" format
    dob = Column(Date)
    age = Column(Integer)
    sex = Column(String(1))  # M, F
    gender = Column(String(50))

    # VA Station
    primary_station = Column(String(10))
    primary_station_name = Column(String(200))

    # Address (primary)
    address_street1 = Column(String(100))
    address_street2 = Column(String(100))
    address_city = Column(String(100))
    address_state = Column(String(2))
    address_zip = Column(String(10))

    # Contact
    phone_primary = Column(String(20))

    # Insurance
    insurance_company_name = Column(String(100))

    # Additional Demographics
    marital_status = Column(String(25))
    religion = Column(String(50))

    # Military Service
    service_connected_percent = Column(DECIMAL(5, 2))

    # Critical Information
    deceased_flag = Column(String(1))
    death_date = Column(Date)

    # Metadata
    veteran_status = Column(String(50))
    source_system = Column(String(20))
    last_updated = Column(TIMESTAMP, default=datetime.utcnow)

    def __repr__(self):
        return f"<Patient(icn={self.icn}, name={self.name_display})>"


class PatientVital(Base):
    """
    Patient vital signs model (clinical.patient_vitals table).

    med-z4 WRITES to this table to create test vitals for patients.
    """
    __tablename__ = "patient_vitals"
    __table_args__ = {"schema": "clinical"}

    # Primary Key
    vital_id = Column(Integer, primary_key=True, autoincrement=True)

    # Patient Reference
    patient_key = Column(String(50), nullable=False)  # Foreign key to patient_demographics

    # Vital Identification
    vital_sign_id = Column(Integer, unique=True, nullable=False)  # Unique across sources
    vital_type = Column(String(100), nullable=False)  # BLOOD PRESSURE, TEMPERATURE, etc.
    vital_abbr = Column(String(10), nullable=False)  # BP, T, WT, HT, P

    # Measurement
    taken_datetime = Column(TIMESTAMP, nullable=False)
    entered_datetime = Column(TIMESTAMP)
    result_value = Column(String(50))  # Display value (e.g., "120/80", "98.6")
    numeric_value = Column(DECIMAL(10, 2))  # For single-value vitals
    systolic = Column(Integer)  # BP only
    diastolic = Column(Integer)  # BP only
    metric_value = Column(DECIMAL(10, 2))  # Converted value
    unit_of_measure = Column(String(20))  # mmHg, F, lb, in, /min

    # Context
    location_id = Column(Integer)
    location_name = Column(String(100))
    location_type = Column(String(50))
    entered_by = Column(String(100))
    abnormal_flag = Column(String(20))  # CRITICAL, HIGH, LOW, NORMAL
    bmi = Column(DECIMAL(5, 2))

    # Metadata
    data_source = Column(String(20), default="med-z4")  # Tag med-z4-created data
    last_updated = Column(TIMESTAMP, default=datetime.utcnow)

    def __repr__(self):
        return f"<Vital(patient={self.patient_key}, type={self.vital_type}, value={self.result_value})>"


class PatientAllergy(Base):
    """
    Patient allergy model (clinical.patient_allergies table).

    med-z4 WRITES to this table to create test allergies for patients.
    """
    __tablename__ = "patient_allergies"
    __table_args__ = {"schema": "clinical"}

    # Primary Key
    allergy_id = Column(Integer, primary_key=True, autoincrement=True)

    # Patient Reference
    patient_key = Column(String(50), nullable=False)

    # Allergy Identification
    allergy_sid = Column(Integer, unique=True, nullable=False)
    allergen_local = Column(String(255), nullable=False)
    allergen_standardized = Column(String(100), nullable=False)
    allergen_type = Column(String(50), nullable=False)  # DRUG, FOOD, ENVIRONMENTAL

    # Severity
    severity = Column(String(50))  # MILD, MODERATE, SEVERE
    severity_rank = Column(Integer)  # 1=MILD, 2=MODERATE, 3=SEVERE

    # Reactions
    reactions = Column(Text)  # Comma-separated for display
    reaction_count = Column(Integer, default=0)

    # Dates
    origination_date = Column(TIMESTAMP, nullable=False)
    observed_date = Column(TIMESTAMP)
    historical_or_observed = Column(String(20))  # HISTORICAL or OBSERVED

    # Context
    originating_site = Column(String(10))
    originating_site_name = Column(String(100))
    originating_staff = Column(String(100))
    comment = Column(Text)  # May contain PHI

    # Status
    is_active = Column(Boolean, default=True)
    verification_status = Column(String(30))
    is_drug_allergy = Column(Boolean, default=False)

    # Metadata
    last_updated = Column(TIMESTAMP, default=datetime.utcnow)

    def __repr__(self):
        return f"<Allergy(patient={self.patient_key}, allergen={self.allergen_standardized})>"


class ClinicalNote(Base):
    """
    Clinical note model (clinical.patient_clinical_notes table).

    med-z4 WRITES to this table to create test clinical notes for patients.
    """
    __tablename__ = "patient_clinical_notes"
    __table_args__ = {"schema": "clinical"}

    # Primary Key
    note_id = Column(Integer, primary_key=True, autoincrement=True)

    # Patient Reference
    patient_key = Column(String(50), nullable=False)

    # Note Identification
    tiu_document_sid = Column(Integer, unique=True, nullable=False)
    document_definition_sid = Column(Integer, nullable=False)
    document_title = Column(String(200), nullable=False)
    document_class = Column(String(50), nullable=False)  # Progress Notes, Consults, etc.
    vha_standard_title = Column(String(200))
    status = Column(String(50), nullable=False)  # COMPLETED

    # Dates
    reference_datetime = Column(TIMESTAMP, nullable=False)  # Clinical date
    entry_datetime = Column(TIMESTAMP, nullable=False)  # Authored date
    days_since_note = Column(Integer)
    note_age_category = Column(String(20))  # <30 days, 30-90 days, etc.

    # Author
    author_sid = Column(Integer)
    author_name = Column(String(200))
    cosigner_sid = Column(Integer)
    cosigner_name = Column(String(200))

    # Context
    visit_sid = Column(Integer)
    sta3n = Column(String(10))
    facility_name = Column(String(200))

    # Content
    document_text = Column(Text)  # Full note narrative (SENSITIVE)
    text_length = Column(Integer)
    text_preview = Column(String(500))  # First 200 chars

    # Metadata
    tiu_document_ien = Column(String(50))
    source_system = Column(String(50), default="med-z4")
    last_updated = Column(TIMESTAMP, default=datetime.utcnow)

    def __repr__(self):
        return f"<Note(patient={self.patient_key}, title={self.document_title})>"
```

**Learning Note: SQLAlchemy Model Conventions**

- **Column names:** Match PostgreSQL schema exactly (snake_case)
- **Column types:** Match database types (String, Integer, DECIMAL, TIMESTAMP)
- **nullable=False:** Required fields (database enforces)
- **unique=True:** Unique constraint (database enforces)
- **default=:** Default value for new records
- **__repr__:** Readable string representation for debugging

### 9.4 CRUD Routes (app/routes/crud.py)

FastAPI routes for creating clinical data:

```python
# app/routes/crud.py
# CRUD operations for clinical data (Phase 6-8)

from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import Dict
import random

from database import get_db
from app.middleware.auth import get_current_user
from app.models.clinical import PatientDemographics, PatientVital, PatientAllergy, ClinicalNote
from app.services.patient_service import generate_unique_icn
import logging

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


# ============================================================================
# Patient CRUD
# ============================================================================

@router.get("/patients/new", response_class=HTMLResponse)
async def new_patient_form(
    request: Request,
    user: Dict = Depends(get_current_user)
):
    """
    Display new patient form.

    GET /patients/new

    Returns:
        HTML form for creating new patient
    """
    return templates.TemplateResponse("patient_create.html", {
        "request": request,
        "user": user,
    })


@router.post("/patients/new")
async def create_patient(
    request: Request,
    name_first: str = Form(...),
    name_last: str = Form(...),
    dob: date = Form(...),
    sex: str = Form(...),
    ssn_last4: str = Form(None),
    address_city: str = Form(None),
    address_state: str = Form(None),
    user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create new patient record.

    POST /patients/new

    Form Data:
        name_first, name_last: Required
        dob: Date of birth (YYYY-MM-DD)
        sex: M or F
        ssn_last4: Optional last 4 of SSN
        address_city, address_state: Optional

    Returns:
        Redirect to dashboard on success
        Form with error message on failure

    Side Effects:
        - Inserts row into clinical.patient_demographics
        - Generates unique ICN in 999 series
        - Sets patient_key = icn (med-z1 pattern)
    """
    try:
        # Generate unique ICN
        icn = generate_unique_icn(db)

        # Calculate age from DOB
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        # Create patient record
        patient = PatientDemographics(
            patient_key=icn,  # patient_key = icn for med-z1 compatibility
            icn=icn,
            name_first=name_first,
            name_last=name_last,
            name_display=f"{name_last.upper()}, {name_first.title()}",
            dob=dob,
            age=age,
            sex=sex,
            ssn_last4=ssn_last4,
            address_city=address_city,
            address_state=address_state,
            primary_station="999",  # Test data marker
            primary_station_name="med-z4 Test Data",
            veteran_status="Veteran",
            source_system="med-z4",
            last_updated=datetime.utcnow(),
        )

        db.add(patient)
        db.commit()

        logger.info(f"Patient created: {icn} ({name_display})")

        # Redirect to dashboard
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        logger.error(f"Error creating patient: {e}")
        db.rollback()

        return templates.TemplateResponse("patient_create.html", {
            "request": request,
            "user": user,
            "error": f"Failed to create patient: {str(e)}"
        }, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# Vital Signs CRUD
# ============================================================================

@router.post("/patients/{patient_icn}/vitals/new")
async def create_vital(
    patient_icn: str,
    vital_type: str = Form(...),
    result_value: str = Form(...),
    taken_datetime: datetime = Form(None),
    user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create new vital sign for patient.

    POST /patients/{patient_icn}/vitals/new

    Form Data:
        vital_type: "BLOOD PRESSURE", "TEMPERATURE", "WEIGHT", "HEIGHT", "PULSE"
        result_value: Display value (e.g., "120/80", "98.6", "180")
        taken_datetime: Optional (defaults to now)

    Returns:
        Redirect to patient detail page

    Side Effects:
        - Inserts row into clinical.patient_vitals
        - Generates unique vital_sign_id
        - Parses result_value for systolic/diastolic (BP only)
    """
    try:
        # Default to current time if not provided
        if not taken_datetime:
            taken_datetime = datetime.utcnow()

        # Map vital type to abbreviation
        vital_abbr_map = {
            "BLOOD PRESSURE": "BP",
            "TEMPERATURE": "T",
            "WEIGHT": "WT",
            "HEIGHT": "HT",
            "PULSE": "P",
        }
        vital_abbr = vital_abbr_map.get(vital_type, "OTHER")

        # Generate unique vital_sign_id (negative to avoid collision with ETL data)
        vital_sign_id = -random.randint(100000, 999999)

        # Parse BP values if applicable
        systolic = None
        diastolic = None
        numeric_value = None

        if vital_type == "BLOOD PRESSURE" and "/" in result_value:
            parts = result_value.split("/")
            systolic = int(parts[0])
            diastolic = int(parts[1])
        else:
            try:
                numeric_value = float(result_value)
            except ValueError:
                numeric_value = None

        # Create vital record
        vital = PatientVital(
            patient_key=patient_icn,
            vital_sign_id=vital_sign_id,
            vital_type=vital_type,
            vital_abbr=vital_abbr,
            taken_datetime=taken_datetime,
            entered_datetime=datetime.utcnow(),
            result_value=result_value,
            numeric_value=numeric_value,
            systolic=systolic,
            diastolic=diastolic,
            unit_of_measure="mmHg" if vital_type == "BLOOD PRESSURE" else None,
            entered_by=user["display_name"],
            data_source="med-z4",
            last_updated=datetime.utcnow(),
        )

        db.add(vital)
        db.commit()

        logger.info(f"Vital created for {patient_icn}: {vital_type} = {result_value}")

        # Redirect to patient detail page
        return RedirectResponse(
            url=f"/patients/{patient_icn}",
            status_code=status.HTTP_303_SEE_OTHER
        )

    except Exception as e:
        logger.error(f"Error creating vital: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create vital: {str(e)}"
        )


# ============================================================================
# Allergy CRUD
# ============================================================================

@router.post("/patients/{patient_icn}/allergies/new")
async def create_allergy(
    patient_icn: str,
    allergen_name: str = Form(...),
    allergen_type: str = Form(...),
    severity: str = Form(...),
    reactions: str = Form(None),
    user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create new allergy for patient.

    POST /patients/{patient_icn}/allergies/new

    Form Data:
        allergen_name: Allergen name (e.g., "PENICILLIN", "SHELLFISH")
        allergen_type: "DRUG", "FOOD", or "ENVIRONMENTAL"
        severity: "MILD", "MODERATE", or "SEVERE"
        reactions: Optional comma-separated reactions (e.g., "Hives, Itching")

    Returns:
        Redirect to patient detail page
    """
    try:
        # Generate unique allergy_sid (negative to avoid collision)
        allergy_sid = -random.randint(100000, 999999)

        # Map severity to rank
        severity_rank_map = {"MILD": 1, "MODERATE": 2, "SEVERE": 3}
        severity_rank = severity_rank_map.get(severity, 1)

        # Count reactions
        reaction_count = len(reactions.split(",")) if reactions else 0

        # Create allergy record
        allergy = PatientAllergy(
            patient_key=patient_icn,
            allergy_sid=allergy_sid,
            allergen_local=allergen_name,
            allergen_standardized=allergen_name.upper(),
            allergen_type=allergen_type,
            severity=severity,
            severity_rank=severity_rank,
            reactions=reactions,
            reaction_count=reaction_count,
            origination_date=datetime.utcnow(),
            observed_date=datetime.utcnow(),
            historical_or_observed="OBSERVED",
            originating_site="999",
            originating_site_name="med-z4 Test Data",
            originating_staff=user["display_name"],
            is_active=True,
            is_drug_allergy=(allergen_type == "DRUG"),
            last_updated=datetime.utcnow(),
        )

        db.add(allergy)
        db.commit()

        logger.info(f"Allergy created for {patient_icn}: {allergen_name}")

        return RedirectResponse(
            url=f"/patients/{patient_icn}",
            status_code=status.HTTP_303_SEE_OTHER
        )

    except Exception as e:
        logger.error(f"Error creating allergy: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create allergy: {str(e)}"
        )


# ============================================================================
# Clinical Note CRUD
# ============================================================================

@router.post("/patients/{patient_icn}/notes/new")
async def create_note(
    patient_icn: str,
    document_title: str = Form(...),
    document_class: str = Form(...),
    document_text: str = Form(...),
    reference_datetime: datetime = Form(None),
    user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create new clinical note for patient.

    POST /patients/{patient_icn}/notes/new

    Form Data:
        document_title: Note title (e.g., "GENERAL MEDICINE PROGRESS NOTE")
        document_class: "Progress Notes", "Consults", "Discharge Summaries", "Imaging"
        document_text: Full note narrative (SOAP format or free text)
        reference_datetime: Optional clinical date (defaults to now)

    Returns:
        Redirect to patient detail page
    """
    try:
        # Default to current time
        if not reference_datetime:
            reference_datetime = datetime.utcnow()

        # Generate unique tiu_document_sid (negative)
        tiu_document_sid = -random.randint(100000, 999999)

        # Calculate text preview (first 200 chars)
        text_preview = document_text[:200] if document_text else ""

        # Create note record
        note = ClinicalNote(
            patient_key=patient_icn,
            tiu_document_sid=tiu_document_sid,
            document_definition_sid=999,  # Test data marker
            document_title=document_title,
            document_class=document_class,
            status="COMPLETED",
            reference_datetime=reference_datetime,
            entry_datetime=datetime.utcnow(),
            author_name=user["display_name"],
            sta3n="999",
            facility_name="med-z4 Test Data",
            document_text=document_text,
            text_length=len(document_text),
            text_preview=text_preview,
            source_system="med-z4",
            last_updated=datetime.utcnow(),
        )

        db.add(note)
        db.commit()

        logger.info(f"Note created for {patient_icn}: {document_title}")

        return RedirectResponse(
            url=f"/patients/{patient_icn}",
            status_code=status.HTTP_303_SEE_OTHER
        )

    except Exception as e:
        logger.error(f"Error creating note: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create note: {str(e)}"
        )
```

**Learning Note: Form Processing Patterns**

- **Form(...):** Required form field (raises error if missing)
- **Form(None):** Optional form field (defaults to None)
- **date.today():** Get current date for age calculation
- **db.add(obj):** Stage object for INSERT
- **db.commit():** Execute INSERT (persist to database)
- **db.rollback():** Undo changes on error
- **Negative IDs:** Use negative IDs for test data to avoid collision with ETL data

---


---

- ETL overwriting med-z4-created data?
- med-z4 duplicating ETL data?
- Data corruption during ETL refreshes?

**Data Ownership Model:**

#### Source System Tagging

All clinical tables include a `source_system` column to identify data origin:

```sql
-- Example: clinical.patient_vitals
source_system VARCHAR(50) NOT NULL DEFAULT 'ETL'
```

**Valid Values:**
- `'ETL'` - Data sourced from med-z1 ETL pipeline (Gold Parquet → PostgreSQL)
- `'med-z4'` - Data created directly by med-z4 application
- `'med-z1'` - Data created by med-z1 (future, if med-z1 adds CRUD)
- `'VistA-RPC'` - Real-time data from VistA RPC Broker (T-0 layer)

#### ICN Namespace Segregation

**ETL Data:**
- Uses real VA ICNs (format: `<digits>V<digits>`, e.g., `100001V123456`)
- Sourced from CDW mock data

**med-z4 Data:**
- Uses **999 series ICNs** (format: `999V######`, e.g., `999V123456`)
- Auto-generated by `generate_unique_icn()` function
- Never conflicts with ETL data (999 series reserved for test/manual entry)

**ICN Generation Function:**

```python
# app/services/patient_service.py
import random
from sqlalchemy import select
from app.models.clinical import PatientDemographics

async def generate_unique_icn(db: AsyncSession) -> str:
    """
    Generate unique 999-series ICN for med-z4 created patients.
    Format: 999V###### where ###### is random 6-digit number.

    Retries up to 10 times if collision detected.
    """
    for attempt in range(10):
        suffix = random.randint(100000, 999999)
        candidate_icn = f"999V{suffix}"

        # Check if ICN already exists
        result = await db.execute(
            select(PatientDemographics.patient_key)
            .where(PatientDemographics.patient_key == candidate_icn)
        )
        if result.scalar_one_or_none() is None:
            return candidate_icn

    raise Exception("Failed to generate unique ICN after 10 attempts")
```

#### ETL Refresh Behavior

**Current ETL Pattern (med-z1):**
1. **Truncate and Reload:** ETL drops all rows with `source_system='ETL'` and reloads from Gold Parquet
2. **Preserves Non-ETL Data:** Rows with `source_system='med-z4'` are **NOT deleted**
3. **No Merging:** ETL does not attempt to update existing rows

**SQL Pattern (Example for patient_vitals):**

```sql
-- ETL load script (simplified)
BEGIN;

-- Delete only ETL-sourced rows
DELETE FROM clinical.patient_vitals
WHERE source_system = 'ETL';

-- Load fresh data from Gold Parquet
COPY clinical.patient_vitals (patient_key, vital_date, systolic, ...)
FROM '/data/gold/vitals.parquet'
WITH (FORMAT parquet);

-- Tag all new rows as ETL-sourced
UPDATE clinical.patient_vitals
SET source_system = 'ETL', last_updated = NOW()
WHERE source_system IS NULL;

COMMIT;
```

**Result:** med-z4-created vitals (tagged `source_system='med-z4'`) survive ETL refreshes.

#### Required Columns for med-z4 Inserts

To ensure compatibility with ETL expectations and downstream queries, med-z4 must populate these fields on every INSERT:

**Patient Demographics:**
```python
PatientDemographics(
    patient_key=icn,                 # 999V###### format
    icn=icn,                         # Same as patient_key (for now)
    name_display=f"{last_name}, {first_name}",
    first_name=first_name,
    last_name=last_name,
    date_of_birth=date_of_birth,
    gender=gender,
    source_system="med-z4",          # REQUIRED
    last_updated=datetime.utcnow()   # REQUIRED
)
```

**Clinical Data (Vitals, Allergies, Notes):**
```python
PatientVital(
    patient_key=patient_key,         # FK to patient_demographics
    vital_date=vital_datetime,
    systolic=systolic,
    diastolic=diastolic,
    # ... other vital fields
    source_system="med-z4",          # REQUIRED
    last_updated=datetime.utcnow()   # REQUIRED
)
```

#### Sandcastle Data Model (Phase 1-8 Limitation)

**What is "Sandcastle Data"?**
Data created in med-z4 is **ephemeral** - it exists only until the next ETL refresh that clears the test environment.

**Why?**
- Development/testing environment only
- ETL pipeline may reset entire database during major refreshes
- 999-series ICNs are for testing, not production use

**User Communication:**
Add visible indicator in med-z4 UI:
```html
<div class="alert alert-warning">
  ⚠️ Test Data: Patients created in med-z4 are for testing only.
  Data may be cleared during ETL refreshes.
</div>
```

**Future Production Pattern:**
- ETL would only load data for **non-999 ICNs**
- 999-series data would persist (production test patients)
- Or, use separate `environment` column: `'dev'` vs `'prod'`

#### Concurrency and Integrity

**Uniqueness Enforcement:**
- `patient_key` is PRIMARY KEY (enforced by database)
- `generate_unique_icn()` checks for collisions before INSERT
- Transactional INSERT with retry logic (see function above)

**Last Write Wins:**
- No optimistic locking in Phase 1-8
- If two users edit same vital simultaneously, last UPDATE wins
- `last_updated` timestamp tracks most recent change

**Future Enhancement (Phase 9+):**
Add `version` column for optimistic locking:
```python
# Check version before UPDATE
result = await db.execute(
    update(PatientVital)
    .where(PatientVital.id == vital_id)
    .where(PatientVital.version == current_version)  # Optimistic lock
    .values(systolic=new_value, version=current_version + 1)
)
if result.rowcount == 0:
    raise HTTPException(409, "Vital was modified by another user. Please refresh.")
```

---


---

## 10. Implementation Roadmap

**UI/UX Implementation Guide:** For detailed wireframes, complete HTML/CSS code, and step-by-step UI implementation instructions, see the **Implementation Mapping Guide** in `docs/spec/med-z4-roadmap-ui-mapping.md`. This guide provides:
- Phase-by-phase mapping to Section 15 (UI/UX Design)
- Complete code snippets for all routes and templates
- Troubleshooting guidance for common UI issues
- Learning resources organized by phase

**Quick Reference:** Each phase below now includes direct links to Section 15 subsections (e.g., "→ Section 15.2" means see Section 15.2 for complete wireframes and code).

---

### Phase 1: Foundation & Environment (Days 1-2)

**Goal:** Set up repository, dependencies, database connectivity

**Tasks:**
1. **Initialize Repository**
   - Create `med-z4` directory
   - `git init` and initial commit
   - Create `.gitignore` (Python, IDE, `.env`)
   - Create `README.md` with quick start guide

2. **Dependencies**
   - Create `requirements.txt` with pinned versions:
     ```
     fastapi==0.109.0
     uvicorn[standard]==0.27.0
     jinja2==3.1.3
     python-multipart==0.0.6
     sqlalchemy==2.0.25
     psycopg2-binary==2.9.9
     bcrypt==4.1.2
     httpx==0.26.0
     python-dotenv==1.0.1
     ```
   - Create virtual environment: `python3.11 -m venv .venv`
   - Install dependencies: `pip install -r requirements.txt`

3. **Configuration**
   - Create `.env.example` (template with placeholders)
   - Create `.env` (actual credentials, NOT in git)
   - Create `config.py` (loads .env, validates)

4. **Database Connectivity**
   - Create `database.py` (SQLAlchemy engine)
   - Test connection to medz1 database:
     ```python
     from database import engine
     with engine.connect() as conn:
         result = conn.execute("SELECT 1")
         print("Database connected!")
     ```

**Verification:**
- `python -c "from config import DATABASE_URL; print('Config OK')"` succeeds
- Database test script connects without errors
- Virtual environment activated

---

### Phase 2: Authentication (Days 2-3)

**Goal:** Implement password authentication and session management

**Tasks:**
1. **Models**
   - Create `app/models/auth.py`
   - Define User, Session, AuditLog models
   - Test models: `from app.models.auth import User; print(User.__tablename__)`

2. **Authentication Service**
   - Create `app/services/auth_service.py`
   - Implement `verify_password()` (bcrypt)
   - Implement `authenticate_user()` (query users, verify password)
   - Implement `create_session()` (insert into auth.sessions)
   - Test with existing med-z1 users

3. **Login Routes**
   - Create `app/routes/auth.py`
   - Implement `GET /login` (display form)
   - Implement `POST /login` (process credentials)
   - Implement `POST /logout` (invalidate session)

4. **Templates** → **See Section 15 for detailed wireframes and complete code**
   - Create `templates/base.html` (Teal theme layout) → **Section 15.8**
   - Create `templates/login.html` (password form) → **Section 15.2**
   - Add CSS in `static/css/style.css` (CSS variables) → **Section 15.1**
   - Add CSS in `static/css/login.css` (login-specific) → **Section 15.2**

5. **Session Middleware**
   - Create `app/middleware/auth.py`
   - Implement `get_current_user()` dependency
   - Test protected routes redirect to login

**Verification:**
- Visit http://localhost:8005/login
- Log in with test credentials (clinician.alpha@va.gov / VaDemo2025!)
- Session cookie (`med_z4_session_id`) appears in browser
- Query auth.sessions table, see new row
- Logout clears cookie

---

### Phase 3: Patient Roster & CCOW Integration (Days 3-4)

**Goal:** Display patient list, implement CCOW context operations

**Tasks:**
1. **Clinical Models**
   - Create `app/models/clinical.py`
   - Define PatientDemographics model (read-only for Phase 3)

2. **CCOW Client**
   - Create `app/services/ccow_client.py`
   - Implement `get_context()`, `set_context()`, `clear_context()`
   - Test against CCOW vault (start with `uvicorn ccow.main:app --port 8001`)

3. **Dashboard Route**
   - Create `app/routes/dashboard.py`
   - Implement `GET /dashboard` (query all patients)
   - Display patient table with Select buttons

4. **Context Routes**
   - Create `app/routes/context.py`
   - Implement `POST /context/set/{patient_icn}`
   - Implement `DELETE /context/clear`
   - Implement `GET /context/active` (HTMX partial)
   - Implement `GET /context/debug` (HTMX partial)

5. **Templates** → **See Section 15 for detailed wireframes and complete code**
   - Create `templates/dashboard.html` (patient roster table) → **Section 15.3**
   - Create `templates/partials/ccow_banner.html` → **Section 15.3**
   - Add CSS in `static/css/dashboard.css` → **Section 15.3**
   - Add HTMX library to `static/js/` → **Section 15.7 (HTMX Patterns)**

**Verification:**
- Dashboard displays all patients from clinical.patient_demographics
- Click "Select" button → active patient banner updates
- CCOW debug panel shows "Online" status
- Check CCOW vault history: http://localhost:8001/ccow/history?scope=global

---

### Phase 4: Two-Application CCOW Testing (Day 4)

**Goal:** Validate context synchronization between med-z1 and med-z4

**Tasks:**
1. **Start Both Applications**
   - Terminal 1: `uvicorn ccow.main:app --port 8001 --reload` (CCOW vault)
   - Terminal 2: `cd med-z1 && uvicorn app.main:app --port 8000 --reload` (med-z1)
   - Terminal 3: `cd med-z4 && uvicorn main:app --port 8005 --reload` (med-z4)

2. **Test Scenario A: med-z4 Drives Context**
   - Browser Tab A: http://localhost:8000 (med-z1)
   - Browser Tab B: http://localhost:8005 (med-z4)
   - Log into both (same user or different users)
   - med-z4: Select patient ICN100001
   - med-z1: Refresh → Active patient should be ICN100001
   - Verify CCOW vault: http://localhost:8001/ccow/active-patients

3. **Test Scenario B: med-z1 Drives Context**
   - med-z1: Search for patient ICN100010, click "Select"
   - med-z4: Wait 5 seconds (HTMX polling) → Active patient should update to ICN100010
   - Verify active patient banner changes color (highlights current context)

4. **Test Scenario C: Context Clear**
   - Either app: Click "Clear Context"
   - Both apps: Should show "NO ACTIVE CONTEXT" after polling interval

**Success Criteria:**
- Context changes propagate within 5 seconds
- No errors in browser console or terminal logs
- CCOW vault history shows all set/clear events

---

### Phase 5: UI Polish & Error Handling (Day 5)

**Goal:** Improve UX, add error handling, prepare for CRUD phases

**Tasks:**
1. **Error Handling**
   - Add try/except blocks in routes
   - Return user-friendly error messages
   - Log errors with context (user, patient_icn, timestamp)

2. **Loading States**
   - Add HTMX indicators: `htmx-indicator` class
   - Show "Loading..." during CCOW operations

3. **Visual Polish**
   - Refine Teal theme colors
   - Add hover states to buttons
   - Responsive layout (mobile-friendly table)
   - Add tooltips to CCOW debug panel

4. **Documentation**
   - Update README.md with setup instructions
   - Add inline code comments
   - Document environment variables

**Deliverables:**
- med-z4 is production-ready for CCOW testing
- All Phase 1-5 features complete and tested

---

### Phase 6: Patient CRUD (Days 5-6)

**Goal:** Enable creation of new patients with 999 series ICNs

**Tasks:**
1. **Patient Service**
   - Create `app/services/patient_service.py`
   - Implement `generate_unique_icn()` (999V######)
   - Implement `icn_exists()` check

2. **CRUD Routes**
   - Create `app/routes/crud.py`
   - Implement `GET /patients/new` (form)
   - Implement `POST /patients/new` (create patient)

3. **Templates** → **See Section 15 for detailed wireframes and complete code**
   - Create `templates/patient_form.html` (new patient form) → **Section 15.5**
   - Add CSS in `static/css/forms.css` → **Section 15.5**
   - Fields: name_first, name_last, dob, sex, ssn (see Section 15.5 wireframe)

4. **Testing**
   - Create patient via med-z4
   - Verify patient appears in med-z1 patient search
   - Select patient in med-z1 → Context synchronizes

**Verification:**
- New patient with ICN 999V123456 created
- Patient visible in both med-z1 and med-z4
- ICN format distinguishes from ETL data

---

### Phase 7: Clinical Data CRUD (Days 6-7)

**Goal:** Add vitals, allergies, clinical notes for patients

**Tasks:**
1. **Extend Models**
   - Complete PatientVital, PatientAllergy, ClinicalNote models

2. **CRUD Routes**
   - Implement `POST /patients/{icn}/vitals/new`
   - Implement `POST /patients/{icn}/allergies/new`
   - Implement `POST /patients/{icn}/notes/new`

3. **Templates** → **See Section 15 for detailed wireframes and complete code**
   - Create `templates/vital_form.html` → **Section 15.6**
   - Create `templates/allergy_form.html` (follow pattern from Section 15.5/15.6)
   - Create `templates/note_form.html` (follow pattern from Section 15.5/15.6)

4. **Patient Detail Page** → **See Section 15 for detailed wireframes and complete code**
   - Create `GET /patients/{icn}` route
   - Create `templates/patient_detail.html` → **Section 15.4**
   - Add CSS in `static/css/patient_detail.css` → **Section 15.4**
   - Display patient info + collapsible sections for vitals, allergies, notes (Alpine.js)
   - Each section has "Add New" button
   - HTMX delete pattern with animation → **Section 15.7 Pattern 3**

**Verification:**
- Add vital for patient 999V123456: BP 120/80
- Open med-z1 → Vital appears in Vitals widget
- Add allergy: PENICILLIN, SEVERE
- Open med-z1 → Red allergy badge increments

---

### Phase 8: Integration & Documentation (Day 8)

**Goal:** Final testing, documentation, handoff

**Tasks:**
1. **End-to-End Testing**
   - Create patient in med-z4
   - Add vitals, allergies, notes
   - Set context in med-z4
   - Verify all data visible in med-z1

2. **Documentation**
   - Finalize README.md
   - Add API documentation (FastAPI /docs)
   - Add troubleshooting guide
   - Document known limitations (sandcastle data)

3. **Code Cleanup**
   - Remove debug print statements
   - Add type hints to all functions
   - Run linter (ruff, black)
   - Add docstrings to all modules

**Deliverables:**
- Fully functional med-z4 application (Phases 1-8)
- Comprehensive documentation
- Ready for deployment to shared development environment

---

## 11. Testing Strategy

### 11.1 Manual Testing Checklist

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
- [ ] CCOW vault history shows all events

**Patient CRUD:**
- [ ] New patient form validates required fields
- [ ] Creating patient generates unique 999 series ICN
- [ ] New patient appears in roster immediately
- [ ] Duplicate ICN creation prevented

**Clinical Data CRUD:**
- [ ] Adding vital for patient succeeds
- [ ] Vital appears in med-z1 Vitals widget
- [ ] Adding allergy increases med-z1 allergy badge count
- [ ] Clinical note appears in med-z1 Notes page
- [ ] med-z4-created data tagged with source_system='med-z4'

### 11.2 Database Verification Queries

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
WHERE s.is_active = TRUE
  AND s.user_agent LIKE '%med-z4%';

-- Verify CCOW context changes
SELECT *
FROM auth.audit_logs
WHERE event_type IN ('ccow_set', 'ccow_clear')
ORDER BY event_timestamp DESC
LIMIT 20;
```

---

## 12. Known Limitations & Future Enhancements

### 12.1 Phase 1-8 Limitations

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

**Single-User CCOW:**
- CCOW context is per-user, but med-z4 doesn't enforce single-session per user
- User can log in twice (two browser tabs) with different contexts
- **Future:** Add session conflict detection

### 12.2 Future Enhancements (Post-Phase 8)

**Phase 9: Advanced CRUD**
- Update patient demographics (PATCH)
- Delete patients and cascade to clinical data
- Bulk operations (import CSV of patients)

**Phase 10: Data Validation**
- Pydantic schemas for form validation
- Business rule enforcement (duplicate SSN, invalid DOB)
- Real-time validation with HTMX

**Phase 11: Search & Filter**
- Full-text search on patient names
- Filter patients by demographics (age range, sex, station)
- Pagination for large patient lists

**Phase 12: Audit Trail**
- View all med-z4 data creation events
- Export audit logs to CSV
- Filter by user, date range, data type

**Phase 13: ETL Integration**
- Mark med-z4 data as "protected" (exclude from ETL wipe)
- Sync med-z4 data to mock CDWWork (persist across ETL runs)
- ETL mode toggle (test vs. persistent data)

---

## 13. Deployment Considerations

### 13.1 Development Environment

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

### 13.2 Shared Development Environment

**Future Deployment (Post-Phase 8):**
- Deploy to shared development server (e.g., dev.va.gov)
- HTTPS required (Let's Encrypt)
- Nginx reverse proxy
- Multiple concurrent users

**Configuration Changes:**
- Set `secure=True` for session cookies (HTTPS only)
- Update CCOW_BASE_URL to production vault URL
- Use connection pooling (QueuePool, not NullPool)
- Add rate limiting (protect against abuse)

### 13.3 Production Considerations

**Not Recommended for Production:**
med-z4 is designed as a **development/testing tool**, not a production EHR system.

**If Deployed to Production:**
- [ ] Implement role-based access control (RBAC)
- [ ] Add comprehensive audit logging
- [ ] Encrypt sensitive data at rest (SSN, patient names)
- [ ] Add HIPAA compliance controls
- [ ] Implement data retention policies
- [ ] Add backup/recovery procedures
- [ ] Security audit and penetration testing

---

**End of Section 4**

---


---


#### CSRF Protection

**Current State (Phase 1-8):** No CSRF protection (simplified development)

**Production Requirement:** Add CSRF tokens to all POST/PUT/DELETE forms

**FastAPI Implementation:**

```bash
pip install fastapi-csrf-protect
```

```python
# main.py
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError

@CsrfProtect.load_config
def get_csrf_config():
    return {
        "secret_key": os.getenv("CSRF_SECRET_KEY"),
        "cookie_name": "med_z4_csrf_token",
        "cookie_samesite": "strict"
    }

app = FastAPI()

@app.exception_handler(CsrfProtectError)
def csrf_protect_exception_handler(request, exc):
    return HTMLResponse(content="CSRF token validation failed", status_code=403)
```

**Template Update:**

```html
<form method="POST" action="/patients/new">
  <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
  <!-- rest of form -->
</form>
```

**Note:** HTMX automatically includes CSRF tokens if configured correctly.

#### Rate Limiting

**Current State:** No rate limiting

**Production Requirement:** Prevent brute-force login attempts

**FastAPI Implementation:**

```bash
pip install slowapi
```

```python
# main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply to login route
@app.post("/login")
@limiter.limit("5/minute")  # Max 5 login attempts per minute per IP
async def login(request: Request, ...):
    # ... login logic
```

**Recommended Limits:**
- Login: 5 attempts per minute per IP
- API endpoints: 100 requests per minute per authenticated user
- CCOW context changes: 20 per minute per user (prevent spam)

#### Account Lockout Policy

**Current State:** No account lockout

**Production Requirement:** Temporarily lock accounts after failed login attempts

**Implementation Approach:**

1. Add `failed_login_attempts` and `locked_until` columns to `auth.users`
2. Increment counter on failed login
3. Lock account for 15 minutes after 5 failures
4. Reset counter on successful login

```python
# app/services/auth_service.py
async def handle_failed_login(db: AsyncSession, username: str):
    """Increment failed login counter, lock if threshold exceeded"""
    result = await db.execute(
        update(User)
        .where(User.username == username)
        .values(
            failed_login_attempts=User.failed_login_attempts + 1,
            locked_until=datetime.utcnow() + timedelta(minutes=15)
                if User.failed_login_attempts + 1 >= 5
                else None
        )
        .returning(User.locked_until)
    )
    await db.commit()
    return result.scalar_one_or_none()
```

#### TLS/HTTPS Requirements

**Development:** HTTP on localhost (acceptable)

**Production:** HTTPS only with valid TLS certificate

**Database Connection:**
```bash
# .env (production)
DATABASE_URL=postgresql://med_z4_app:<password>@db-server:5432/medz1?sslmode=require
```

**Application Server:**
```bash
# Use reverse proxy (nginx/Traefik) for TLS termination
# Or use Uvicorn with SSL:
uvicorn main:app --host 0.0.0.0 --port 8005 \
    --ssl-keyfile=/path/to/privkey.pem \
    --ssl-certfile=/path/to/fullchain.pem
```

**Force HTTPS Redirects:**
```python
# middleware/https_redirect.py
from fastapi import Request
from fastapi.responses import RedirectResponse

@app.middleware("http")
async def https_redirect(request: Request, call_next):
    if request.headers.get("x-forwarded-proto") == "http":
        url = request.url.replace(scheme="https")
        return RedirectResponse(url)
    return await call_next(request)
```

#### Security Headers

**Production Requirement:** Add security headers to all responses

```python
# middleware/security_headers.py
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' https://unpkg.com; style-src 'self' 'unsafe-inline'"
    return response
```

#### Production Checklist

- [ ] Enable CSRF protection on all forms
- [ ] Implement rate limiting (login: 5/min, API: 100/min)
- [ ] Add account lockout after 5 failed login attempts
- [ ] Enforce HTTPS only (no HTTP)
- [ ] Require TLS for database connections (`sslmode=require`)
- [ ] Add security headers middleware
- [ ] Use dedicated `med_z4_app` database role (not `postgres`)
- [ ] Enable audit logging for all clinical data access
- [ ] Set secure cookie flags: `secure=True`, `httponly=True`, `samesite='strict'`
- [ ] Disable FastAPI auto-generated docs in production (`docs_url=None`, `redoc_url=None`)
- [ ] Set strong `SECRET_KEY` for session encryption (64+ random characters)
- [ ] Review and remove any hardcoded credentials
- [ ] Enable application-level logging (not just database audit logs)
- [ ] Set up automated security scanning (Dependabot, Snyk, or similar)

**Note:** Many of these items are out of scope for Phase 1-8 (development/testing) but should be implemented before any production deployment.

---

## Summary of Updates

These 7 updates address all peer review feedback:

1. **DB Access Model** - Resolves read-only vs CRUD contradiction
2. **CCOW Cookie Contract** - Clarifies session validation mechanism
3. **Routes Contract Table** - Complete endpoint reference
4. **Patient Identity** - Normalizes patient_key vs icn usage
5. **Data Ownership** - Prevents ETL conflicts with 999-series ICNs
6. **Audit Logging** - Extends to clinical data access
7. **Security Hardening** - Production checklist (CSRF, rate limiting, TLS)

**Next Step:** Integrate these updates into `med-z4-design.md` at the specified section numbers.

---

## 14. References

### Related Documentation

**med-z1 Architecture & Design:**
- `docs/spec/med-z1-architecture.md` - System architecture and design patterns
- `docs/spec/postgresql-database-reference.md` - Complete PostgreSQL schema reference
- `docs/guide/developer-setup-guide.md` - Development environment setup

**CCOW Implementation:**
- `ccow/README.md` - CCOW Context Vault overview
- `ccow/main.py` - CCOW vault v2.0 REST API implementation
- `ccow/auth_helper.py` - Session validation for CCOW operations

**med-z1 Application Code (Reference):**
- `app/models/auth.py` - Authentication models (User, Session, AuditLog)
- `app/routes/auth.py` - Login/logout routes
- `app/middleware/auth.py` - Session validation middleware
- `app/services/ccow_client.py` - CCOW client (DO NOT copy, use as reference)

### External Resources

**FastAPI:**
- Official Documentation: https://fastapi.tiangolo.com/
- Tutorial: https://fastapi.tiangolo.com/tutorial/
- Security: https://fastapi.tiangolo.com/tutorial/security/

**HTMX:**
- Official Documentation: https://htmx.org/docs/
- Examples: https://htmx.org/examples/
- Attributes Reference: https://htmx.org/reference/

**SQLAlchemy:**
- Official Documentation: https://docs.sqlalchemy.org/
- ORM Tutorial: https://docs.sqlalchemy.org/en/20/tutorial/
- Relationship Patterns: https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html

**PostgreSQL:**
- Official Documentation: https://www.postgresql.org/docs/16/
- Data Types: https://www.postgresql.org/docs/16/datatype.html
- Indexes: https://www.postgresql.org/docs/16/indexes.html

**bcrypt:**
- Python bcrypt: https://github.com/pyca/bcrypt
- Password Hashing Best Practices: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html

**HL7 CCOW:**
- HL7 CCOW Standard: http://www.hl7.org/implement/standards/product_brief.cfm?product_id=1
- Context Management: https://www.hl7.org/fhir/contextmanagement.html

### Development Tools

**Recommended:**
- VS Code (IDE): https://code.visualstudio.com/
- Postman (API testing): https://www.postman.com/
- DBeaver (Database GUI): https://dbeaver.io/
- Docker Desktop (Containers): https://www.docker.com/products/docker-desktop/

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

-- View CCOW context history
SELECT user_id, email, patient_id, actor, timestamp
FROM ccow_context_history  -- Hypothetical table from vault
ORDER BY timestamp DESC
LIMIT 20;
```

### Testing CCOW with curl

```bash
# Health check
curl http://localhost:8001/ccow/health

# Get context (requires session cookie)
curl -b "session_id=your-session-uuid" \
  http://localhost:8001/ccow/active-patient

# Set context
curl -X PUT \
  -b "session_id=your-session-uuid" \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"ICN100001","set_by":"med-z4"}' \
  http://localhost:8001/ccow/active-patient
```

---

## Appendix B: Troubleshooting Guide

### Common Issues

**Issue: "Connection refused" to PostgreSQL**
- Check PostgreSQL container is running: `docker ps | grep postgres16`
- Start if needed: `docker start postgres16`
- Verify credentials in `.env` match container password

**Issue: "Session validation failed (401)"**
- Check session cookie exists in browser (Developer Tools → Application → Cookies)
- Verify session exists in database: `SELECT * FROM auth.sessions WHERE session_id = '...'`
- Check session has not expired: `WHERE expires_at > NOW()`

**Issue: "CCOW vault not reachable"**
- Verify CCOW vault is running: `curl http://localhost:8001/ccow/health`
- Check CCOW_BASE_URL in med-z4 `.env` is correct
- Check firewall not blocking port 8001

**Issue: "Patient not appearing in med-z1 after creation in med-z4"**
- Verify patient was inserted: `SELECT * FROM clinical.patient_demographics WHERE icn = '...'`
- Check med-z1 is querying same database (not cached data)
- Hard refresh med-z1 browser (Ctrl+Shift+R or Cmd+Shift+R)

**Issue: "HTMX not updating active patient banner"**
- Check browser console for JavaScript errors (F12 → Console)
- Verify HTMX library loaded: Look for `<script src="/static/js/htmx.min.js"></script>`
- Check HTMX polling interval: `hx-trigger="load, every 5s"`
- Inspect network tab (F12 → Network) to see if GET /context/active requests are happening

**Issue: "bcrypt password verification slow"**
- Expected behavior! bcrypt is intentionally slow (~300ms per hash)
- Do NOT lower BCRYPT_ROUNDS below 12 (reduces security)
- Consider async bcrypt in production (non-blocking)

---

## Appendix C: Learning Resources

### Recommended Learning Path

**For FastAPI Beginners:**
1. FastAPI Tutorial (Official): https://fastapi.tiangolo.com/tutorial/
2. Build a basic CRUD API (practice project)
3. Study med-z4 authentication routes (app/routes/auth.py)
4. Implement your own route with dependency injection

**For HTMX Beginners:**
1. HTMX in 100 Seconds: https://www.youtube.com/watch?v=r-GSGH2RxJs
2. HTMX Examples: https://htmx.org/examples/
3. Study med-z4 dashboard template (templates/dashboard.html)
4. Build a simple counter app with HTMX

**For SQLAlchemy Beginners:**
1. SQLAlchemy Core Tutorial: https://docs.sqlalchemy.org/en/20/tutorial/
2. ORM Quick Start: https://docs.sqlalchemy.org/en/20/orm/quickstart.html
3. Study med-z4 models (app/models/auth.py, app/models/clinical.py)
4. Practice queries with med-z1 database

**For CCOW Beginners:**
1. Read CCOW Context Vault README (ccow/README.md)
2. Test CCOW API with Postman (http://localhost:8001/docs)
3. Study CCOWClient implementation (app/services/ccow_client.py)
4. Build a simple context logger (log all CCOW events to file)

---

## Document Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| v1.0 | 2026-01-22 | Claude Code + Chuck | Initial comprehensive design specification |

---

**End of Document**

*For questions or clarifications, refer to related documentation in `docs/spec/` or consult the med-z1 implementation in the `med-z1` repository.*
# Section 15: UI/UX Design & Wireframes

## 15.1 Design Philosophy

### Core Principles

1. **Simplicity First**: Clean, uncluttered interfaces focused on core tasks
2. **Clinical Clarity**: Important patient data immediately visible with clear visual hierarchy
3. **Teal Theme Identity**: Consistent use of Teal/Emerald colors to distinguish from med-z1
4. **Accessibility**: 508-compliant, keyboard-navigable, high contrast
5. **Server-Side Rendering**: HTMX for dynamic updates without JavaScript complexity
6. **Responsive Layout**: Mobile-friendly but optimized for desktop clinical workflows

### Visual Design System

**Color Palette (Teal Theme)**:
```css
/* Primary Colors */
--primary-teal: #14b8a6;        /* Teal 500 - Primary actions, headers */
--primary-teal-dark: #0f766e;   /* Teal 700 - Hover states */
--primary-teal-light: #5eead4;  /* Teal 300 - Accents, highlights */

/* Semantic Colors */
--success-green: #10b981;       /* Success messages, positive indicators */
--warning-amber: #f59e0b;       /* Warnings, pending states */
--danger-red: #ef4444;          /* Errors, critical alerts */
--info-blue: #3b82f6;           /* Informational messages */

/* Neutral Colors */
--gray-50: #f9fafb;             /* Background, subtle sections */
--gray-100: #f3f4f6;            /* Card backgrounds */
--gray-200: #e5e7eb;            /* Borders, dividers */
--gray-700: #374151;            /* Body text */
--gray-900: #111827;            /* Headings, emphasis */

/* CCOW Context Indicator */
--ccow-active: #14b8a6;         /* Active patient context (Teal) */
--ccow-inactive: #9ca3af;       /* No active context (Gray) */
```

**Typography**:
```css
/* Font Stack */
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
             "Helvetica Neue", Arial, sans-serif;

/* Type Scale */
--text-xs: 0.75rem;     /* 12px - Labels, captions */
--text-sm: 0.875rem;    /* 14px - Secondary text */
--text-base: 1rem;      /* 16px - Body text */
--text-lg: 1.125rem;    /* 18px - Subheadings */
--text-xl: 1.25rem;     /* 20px - Section headings */
--text-2xl: 1.5rem;     /* 24px - Page headings */
--text-3xl: 1.875rem;   /* 30px - Hero text */
```

**Spacing System**:
```css
/* Consistent spacing scale */
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-12: 3rem;     /* 48px */
```

---

## 15.2 Login Screen

### Wireframe

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
│              ║                               ║              │
│              ║  Username:                    ║              │
│              ║  [____________________]       ║              │
│              ║                               ║              │
│              ║  Password:                    ║              │
│              ║  [____________________]       ║              │
│              ║                               ║              │
│              ║       [  Login  ]             ║              │
│              ║                               ║              │
│              ╚═══════════════════════════════╝              │
│                                                             │
│              ┌───────────────────────────────┐              │
│              │ ℹ️  Test Credentials:         │              │
│              │    Username: clinician        │              │
│              │    Password: password         │              │
│              └───────────────────────────────┘              │
│                                                             │
│                  Powered by med-z4 v1.0                     │
└─────────────────────────────────────────────────────────────┘
```

### Design Specifications

**Layout**:
- Centered card on gradient background (Teal gradient: light to dark)
- Card: 400px width, white background, rounded corners (8px), shadow
- Vertical rhythm: 24px spacing between form elements
- Logo/branding at top (80px height)

**Form Elements**:
- Input fields: Full width, 40px height, 2px Teal border on focus
- Labels: 14px, gray-700, bold, 8px margin-bottom
- Login button: Full width, 44px height, Teal background, white text
- Button hover: Darker Teal (teal-700), slight scale (1.02)

**Info Panel**:
- Light blue background (#e0f2fe), blue border-left (4px)
- 16px padding, 14px text, info icon
- Rounded corners (4px)

**Validation**:
- Error messages: Red background, white text, above form
- Field errors: Red border, red text below field
- Success: Green border flash on valid input

### HTML/Jinja2 Template Example

```html
{# templates/login.html #}
{% extends "base.html" %}

{% block title %}Login - med-z4 Simple EHR{% endblock %}

{% block content %}
<div class="login-container">
  <div class="login-card">
    {# Branding #}
    <div class="login-header">
      <div class="logo">
        <svg class="logo-icon" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
        </svg>
        <h1>med-z4</h1>
        <p class="subtitle">Simple EHR Application</p>
      </div>
    </div>

    {# Error Message #}
    {% if error %}
    <div class="alert alert-error" role="alert">
      <svg class="alert-icon" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"/>
      </svg>
      <span>{{ error }}</span>
    </div>
    {% endif %}

    {# Login Form #}
    <form method="POST" action="/login" class="login-form">
      <div class="form-group">
        <label for="username">Username</label>
        <input
          type="text"
          id="username"
          name="username"
          class="form-input"
          required
          autofocus
          autocomplete="username"
          placeholder="Enter your username"
        >
      </div>

      <div class="form-group">
        <label for="password">Password</label>
        <input
          type="password"
          id="password"
          name="password"
          class="form-input"
          required
          autocomplete="current-password"
          placeholder="Enter your password"
        >
      </div>

      <button type="submit" class="btn btn-primary btn-block">
        <span>Login</span>
        <svg class="btn-icon" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M3 3a1 1 0 011 1v12a1 1 0 11-2 0V4a1 1 0 011-1zm7.707 3.293a1 1 0 010 1.414L9.414 9H17a1 1 0 110 2H9.414l1.293 1.293a1 1 0 01-1.414 1.414l-3-3a1 1 0 010-1.414l3-3a1 1 0 011.414 0z"/>
        </svg>
      </button>
    </form>

    {# Test Credentials Info #}
    <div class="info-panel">
      <svg class="info-icon" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"/>
      </svg>
      <div class="info-content">
        <p class="info-title">Test Credentials</p>
        <p class="info-detail">Username: <code>clinician</code></p>
        <p class="info-detail">Password: <code>password</code></p>
      </div>
    </div>
  </div>

  {# Footer #}
  <div class="login-footer">
    <p>Powered by med-z4 v1.0 | Simple EHR for CCOW Testing</p>
  </div>
</div>
{% endblock %}
```

### CSS Example (Teal Theme)

```css
/* static/css/login.css */

/* Login Container - Full viewport with gradient background */
.login-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #5eead4 0%, #14b8a6 50%, #0f766e 100%);
  padding: var(--space-4);
}

/* Login Card - White card with shadow */
.login-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
  width: 100%;
  max-width: 400px;
  padding: var(--space-8);
}

/* Branding Section */
.login-header {
  text-align: center;
  margin-bottom: var(--space-8);
}

.logo {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
}

.logo-icon {
  width: 64px;
  height: 64px;
  color: var(--primary-teal);
}

.logo h1 {
  font-size: var(--text-3xl);
  font-weight: bold;
  color: var(--gray-900);
  margin: 0;
}

.logo .subtitle {
  font-size: var(--text-sm);
  color: var(--gray-700);
  margin: 0;
}

/* Alert Messages */
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

.alert-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

/* Form Styling */
.login-form {
  margin-bottom: var(--space-6);
}

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

.form-input::placeholder {
  color: var(--gray-400);
}

/* Button Styling */
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
  box-shadow: 0 4px 12px rgba(20, 184, 166, 0.3);
}

.btn-primary:active {
  transform: translateY(0);
}

.btn-block {
  width: 100%;
  height: 48px;
}

.btn-icon {
  width: 20px;
  height: 20px;
}

/* Info Panel */
.info-panel {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-4);
  background-color: #e0f2fe;
  border-left: 4px solid var(--info-blue);
  border-radius: 6px;
  font-size: var(--text-sm);
}

.info-icon {
  width: 24px;
  height: 24px;
  color: var(--info-blue);
  flex-shrink: 0;
}

.info-content {
  flex: 1;
}

.info-title {
  font-weight: 600;
  color: var(--gray-900);
  margin: 0 0 var(--space-2) 0;
}

.info-detail {
  margin: var(--space-1) 0;
  color: var(--gray-700);
}

.info-detail code {
  background-color: white;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
  color: var(--primary-teal-dark);
}

/* Footer */
.login-footer {
  margin-top: var(--space-6);
  text-align: center;
  color: white;
  font-size: var(--text-sm);
  opacity: 0.9;
}

/* Responsive Design */
@media (max-width: 640px) {
  .login-card {
    padding: var(--space-6);
  }

  .logo h1 {
    font-size: var(--text-2xl);
  }
}
```

---

## 15.3 Dashboard / Patient Roster Screen

### Wireframe

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ med-z4 Simple EHR                    [CCOW: No Active Patient] [Logout] │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ╔═══════════════════════════════════════════════════════════════════════╗   │
│ ║  Patient Roster                                   [+ Add New Patient] ║   │
│ ╠═══════════════════════════════════════════════════════════════════════╣   │
│ ║                                                                       ║   │
│ ║  ┌─────────┬─────────────┬──────────┬───────────┬──────────────────┐  ║   │
│ ║  │ ICN     │ Name        │ Gender   │ DOB       │ Actions          │  ║   │
│ ║  ├─────────┼─────────────┼──────────┼───────────┼──────────────────┤  ║   │
│ ║  │ 999V... │ Doe, John   │ M        │ 1975-03-15│ [View] [Set CCOW]│  ║   │
│ ║  │ 999V... │ Smith, Jane │ F        │ 1982-07-22│ [View] [Set CCOW]│  ║   │
│ ║  │ 999V... │ Brown, Bob  │ M        │ 1968-11-30│ [View] [Set CCOW]│  ║   │
│ ║  │ 999V... │ Davis, Sue  │ F        │ 1995-01-08│ [View] [Set CCOW]│  ║   │
│ ║  └─────────┴─────────────┴──────────┴───────────┴──────────────────┘  ║   │
│ ║                                                                       ║   │
│ ║  Total Patients: 4                                                    ║   │
│ ╚═══════════════════════════════════════════════════════════════════════╝   │
│                                                                             │
│ ╔═══════════════════════════════════════════════════════════════════════╗   │
│ ║  CCOW Debug Panel                                         [Collapse]  ║   │
│ ╠═══════════════════════════════════════════════════════════════════════╣   │
│ ║  Current Context: None                                                ║   │
│ ║  Last Updated: --                                                     ║   │
│ ║  Session ID: abc123...                                                ║   │
│ ║  [Clear Context] [Refresh]                                            ║   │
│ ╚═══════════════════════════════════════════════════════════════════════╝   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Design Specifications

**Header Bar**:
- Fixed top, full width, Teal background (#14b8a6)
- 60px height, white text, shadow
- Logo/title on left, CCOW status center, logout right
- CCOW badge: Pill shape, changes color based on context (Teal=active, Gray=inactive)

**Patient Roster Table**:
- White background, rounded corners (8px), shadow
- Header row: Teal background, white text, bold
- Data rows: Alternating white/gray-50 (striped), hover effect (gray-100)
- Column widths: ICN (15%), Name (25%), Gender (10%), DOB (15%), Actions (35%)
- Actions: Small buttons, Teal outline, hover fill

**CCOW Debug Panel**:
- Collapsible section, gray-100 background
- Monospace font for technical details
- Clear visual separation from main content
- Auto-refresh every 5 seconds (HTMX polling)

**Add New Patient Button**:
- Teal background, white text, rounded
- Icon + text, hover scale effect
- Positioned top-right of roster card

### HTML/Jinja2 Template Example

```html
{# templates/dashboard.html #}
{% extends "base.html" %}

{% block title %}Patient Roster - med-z4{% endblock %}

{% block content %}
<div class="dashboard-container">
  {# Active Patient Banner (polled every 5 seconds) #}
  <div
    id="ccow-banner"
    class="ccow-banner"
    hx-get="/context/banner"
    hx-trigger="load, every 5s"
    hx-swap="outerHTML"
  >
    {% include "partials/ccow_banner.html" %}
  </div>

  {# Patient Roster Card #}
  <div class="card">
    <div class="card-header">
      <h2 class="card-title">Patient Roster</h2>
      <a href="/patients/new" class="btn btn-primary">
        <svg class="btn-icon" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"/>
        </svg>
        <span>Add New Patient</span>
      </a>
    </div>

    <div class="card-body">
      {% if patients %}
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>ICN</th>
              <th>Name</th>
              <th>Gender</th>
              <th>Date of Birth</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {% for patient in patients %}
            <tr>
              <td class="font-mono">{{ patient.icn }}</td>
              <td class="font-semibold">{{ patient.last_name }}, {{ patient.first_name }}</td>
              <td>
                <span class="badge badge-neutral">{{ patient.gender }}</span>
              </td>
              <td>{{ patient.date_of_birth.strftime('%Y-%m-%d') }}</td>
              <td class="actions-cell">
                <a href="/patients/{{ patient.icn }}" class="btn btn-sm btn-outline">
                  <svg class="btn-icon-sm" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M10 12a2 2 0 100-4 2 2 0 000 4z"/>
                    <path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z"/>
                  </svg>
                  View
                </a>
                <button
                  class="btn btn-sm btn-primary"
                  hx-put="/context/set"
                  hx-vals='{"icn": "{{ patient.icn }}"}'
                  hx-swap="none"
                  hx-on::after-request="if(event.detail.successful) { htmx.trigger('#ccow-banner', 'load'); }"
                >
                  <svg class="btn-icon-sm" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/>
                  </svg>
                  Set CCOW
                </button>
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>

      <div class="table-footer">
        <p class="text-sm text-gray-600">
          Total Patients: <span class="font-semibold">{{ patients|length }}</span>
        </p>
      </div>
      {% else %}
      <div class="empty-state">
        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
        </svg>
        <p class="empty-message">No patients found</p>
        <p class="empty-hint">Click "Add New Patient" to create your first test patient</p>
      </div>
      {% endif %}
    </div>
  </div>

  {# CCOW Debug Panel #}
  <div class="card debug-panel" x-data="{ open: true }">
    <div class="card-header">
      <h3 class="card-title">CCOW Debug Panel</h3>
      <button @click="open = !open" class="btn btn-sm btn-ghost">
        <span x-text="open ? 'Collapse' : 'Expand'"></span>
      </button>
    </div>
    <div class="card-body" x-show="open" x-collapse>
      <div
        id="ccow-debug"
        hx-get="/context/debug"
        hx-trigger="load, every 5s"
        hx-swap="innerHTML"
      >
        {% include "partials/ccow_debug.html" %}
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

### Partial Template: CCOW Banner

```html
{# templates/partials/ccow_banner.html #}
{% if active_patient %}
<div id="ccow-banner" class="ccow-banner ccow-active">
  <div class="ccow-indicator">
    <svg class="ccow-icon" viewBox="0 0 20 20" fill="currentColor">
      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"/>
    </svg>
    <span class="ccow-label">Active Patient Context</span>
  </div>
  <div class="ccow-patient-info">
    <span class="patient-name">{{ active_patient.last_name }}, {{ active_patient.first_name }}</span>
    <span class="patient-icn">ICN: {{ active_patient.icn }}</span>
    <span class="patient-dob">DOB: {{ active_patient.date_of_birth.strftime('%Y-%m-%d') }}</span>
  </div>
  <button
    class="btn btn-sm btn-danger"
    hx-delete="/context/clear"
    hx-swap="none"
    hx-on::after-request="htmx.trigger('#ccow-banner', 'load'); htmx.trigger('#ccow-debug', 'load');"
  >
    Clear Context
  </button>
</div>
{% else %}
<div id="ccow-banner" class="ccow-banner ccow-inactive">
  <div class="ccow-indicator">
    <svg class="ccow-icon" viewBox="0 0 20 20" fill="currentColor">
      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"/>
    </svg>
    <span class="ccow-label">No Active Patient Context</span>
  </div>
  <p class="ccow-hint">Click "Set CCOW" on any patient to activate context synchronization</p>
</div>
{% endif %}
```

### CSS Example (Dashboard)

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

.ccow-banner.ccow-active {
  background: linear-gradient(90deg, #d1fae5 0%, #a7f3d0 100%);
  border-left: 4px solid var(--ccow-active);
}

.ccow-banner.ccow-inactive {
  background: var(--gray-100);
  border-left: 4px solid var(--ccow-inactive);
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

.ccow-active .ccow-icon {
  color: var(--ccow-active);
}

.ccow-inactive .ccow-icon {
  color: var(--ccow-inactive);
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
  background-color: #ccfbf1; /* Teal-100 */
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

/* Button Variants */
.btn-sm {
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  height: auto;
}

.btn-outline {
  background: transparent;
  border: 2px solid var(--primary-teal);
  color: var(--primary-teal);
}

.btn-outline:hover {
  background: var(--primary-teal);
  color: white;
}

.btn-danger {
  background-color: var(--danger-red);
  color: white;
}

.btn-danger:hover {
  background-color: #dc2626;
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

/* Debug Panel */
.debug-panel {
  background-color: var(--gray-50);
  border: 1px solid var(--gray-300);
}

.debug-panel .card-body {
  font-family: 'Courier New', monospace;
  font-size: var(--text-sm);
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

---

## 15.4 Patient Detail Screen

### Wireframe

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ med-z4   [CCOW: Smith, Jane | 999V123456 | DOB: 1982-07-22]   [Logout]  │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ╔═══════════════════════════════════════════════════════════════════════╗   │
│ ║  Patient Details                     [Edit] [Delete] [Set as CCOW]    ║   │
│ ╠═══════════════════════════════════════════════════════════════════════╣   │
│ ║                                                                       ║   │
│ ║  Name:          Smith, Jane                                           ║   │
│ ║  ICN:           999V123456                                            ║   │
│ ║  Date of Birth: July 22, 1982 (42 years old)                         ║   │
│ ║  Gender:        Female                                                ║   │
│ ║  SSN:           ***-**-4567                                           ║   │
│ ║                                                                       ║   │
│ ╚═══════════════════════════════════════════════════════════════════════╝   │
│                                                                             │
│ ╔═══════════════════════════════════════════════════════════════════════╗   │
│ ║  Clinical Data                                                        ║   │
│ ╠═══════════════════════════════════════════════════════════════════════╣   │
│ ║                                                                       ║   │
│ ║  ┌─────────────────────────────────────────────────────────────────┐  ║   │
│ ║  │ 📊 Vital Signs (3)                               [+ Add Vital]  │  ║   │
│ ║  ├─────────────────────────────────────────────────────────────────┤  ║   │
│ ║  │ 2026-01-20  BP: 120/80  HR: 72  Temp: 98.6°F   [Edit] [Delete]  │  ║   │
│ ║  │ 2026-01-15  BP: 118/78  HR: 70  Temp: 98.4°F   [Edit] [Delete]  │  ║   │
│ ║  │ 2026-01-10  BP: 122/82  HR: 74  Temp: 98.7°F   [Edit] [Delete]  │  ║   │
│ ║  └─────────────────────────────────────────────────────────────────┘  ║   │
│ ║                                                                       ║   │
│ ║  ┌─────────────────────────────────────────────────────────────────┐  ║   │
│ ║  │ ⚠️  Allergies (2)                              [+ Add Allergy]  │  ║   │
│ ║  ├─────────────────────────────────────────────────────────────────┤  ║   │
│ ║  │ Penicillin - Severe: Anaphylaxis               [Edit] [Delete]  │  ║   │
│ ║  │ Peanuts - Moderate: Hives, swelling            [Edit] [Delete]  │  ║   │
│ ║  └─────────────────────────────────────────────────────────────────┘  ║   │
│ ║                                                                       ║   │
│ ║  ┌─────────────────────────────────────────────────────────────────┐  ║   │
│ ║  │ 📝 Clinical Notes (1)                            [+ Add Note]   │  ║   │
│ ║  ├─────────────────────────────────────────────────────────────────┤  ║   │
│ ║  │ 2026-01-18 Progress Note by Dr. Johnson        [View] [Delete]  │  ║   │
│ ║  │ "Patient presents with..."                                      │  ║   │
│ ║  └─────────────────────────────────────────────────────────────────┘  ║   │
│ ║                                                                       ║   │
│ ╚═══════════════════════════════════════════════════════════════════════╝   │
│                                                                             │
│ [← Back to Roster]                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Design Specifications

**Patient Header Card**:
- Prominent display of patient identifiers
- Age calculated from DOB (shown in parentheses)
- SSN masked (last 4 digits only)
- Action buttons: Edit, Delete, Set as CCOW (top-right)

**Clinical Data Sections**:
- Collapsible cards for each domain (Vitals, Allergies, Notes)
- Icon indicators for each domain type
- Count badge showing number of records
- Add button for each domain (top-right of section)
- Empty state when no records: "No vitals recorded yet. Click Add Vital to create the first entry."

**Vital Signs Display**:
- Most recent first (reverse chronological)
- Compact single-line format: Date, BP, HR, Temp, Actions
- Color coding for abnormal values (red for critical, amber for borderline)

**Allergies Display**:
- Allergen name in bold
- Severity badge (Severe=Red, Moderate=Amber, Mild=Yellow)
- Reaction description in gray
- Warning icon for severe allergies

**Clinical Notes Display**:
- Date, note type, author
- First 100 characters of note text (truncated with "...")
- View button opens modal/full page

### HTML/Jinja2 Template Example

```html
{# templates/patient_detail.html #}
{% extends "base.html" %}

{% block title %}{{ patient.last_name }}, {{ patient.first_name }} - med-z4{% endblock %}

{% block content %}
<div class="patient-detail-container">
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
          hx-put="/context/set"
          hx-vals='{"icn": "{{ patient.icn }}"}'
          hx-swap="none"
          hx-on::after-request="htmx.trigger('#ccow-banner', 'load');"
        >
          <svg class="btn-icon-sm" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/>
          </svg>
          Set as CCOW
        </button>
        <button
          class="btn btn-sm btn-danger"
          hx-delete="/patients/{{ patient.icn }}"
          hx-confirm="Are you sure you want to delete this patient?"
          hx-target="body"
        >
          <svg class="btn-icon-sm" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"/>
          </svg>
          Delete
        </button>
      </div>
    </div>

    <div class="card-body">
      <dl class="detail-list">
        <div class="detail-item">
          <dt>Name</dt>
          <dd class="patient-name">{{ patient.last_name }}, {{ patient.first_name }}</dd>
        </div>
        <div class="detail-item">
          <dt>ICN</dt>
          <dd class="font-mono">{{ patient.icn }}</dd>
        </div>
        <div class="detail-item">
          <dt>Date of Birth</dt>
          <dd>
            {{ patient.date_of_birth.strftime('%B %d, %Y') }}
            <span class="age-badge">({{ calculate_age(patient.date_of_birth) }} years old)</span>
          </dd>
        </div>
        <div class="detail-item">
          <dt>Gender</dt>
          <dd>
            <span class="badge badge-neutral">{{ patient.gender }}</span>
          </dd>
        </div>
        {% if patient.ssn %}
        <div class="detail-item">
          <dt>SSN</dt>
          <dd class="font-mono">***-**-{{ patient.ssn[-4:] }}</dd>
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
              <span class="vital-date">{{ vital.vital_date.strftime('%Y-%m-%d %H:%M') }}</span>
              <span class="vital-reading">BP: {{ vital.systolic }}/{{ vital.diastolic }}</span>
              <span class="vital-reading">HR: {{ vital.heart_rate }}</span>
              <span class="vital-reading">Temp: {{ vital.temperature }}°F</span>
              <div class="vital-actions">
                <a href="/patients/{{ patient.icn }}/vitals/{{ vital.id }}/edit" class="btn btn-xs btn-outline">Edit</a>
                <button
                  class="btn btn-xs btn-danger"
                  hx-delete="/patients/{{ patient.icn }}/vitals/{{ vital.id }}"
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
            <div class="allergy-item {% if allergy.severity == 'Severe' %}severe{% endif %}">
              <div class="allergy-info">
                <span class="allergen-name">{{ allergy.allergen }}</span>
                <span class="severity-badge severity-{{ allergy.severity.lower() }}">{{ allergy.severity }}</span>
                <span class="reaction-text">{{ allergy.reaction }}</span>
              </div>
              <div class="allergy-actions">
                <a href="/patients/{{ patient.icn }}/allergies/{{ allergy.id }}/edit" class="btn btn-xs btn-outline">Edit</a>
                <button
                  class="btn btn-xs btn-danger"
                  hx-delete="/patients/{{ patient.icn }}/allergies/{{ allergy.id }}"
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
                <span class="note-date">{{ note.note_date.strftime('%Y-%m-%d') }}</span>
                <span class="note-type">{{ note.note_type }}</span>
                <span class="note-author">by {{ note.author }}</span>
              </div>
              <div class="note-preview">
                {{ note.note_text[:100] }}{% if note.note_text|length > 100 %}...{% endif %}
              </div>
              <div class="note-actions">
                <a href="/patients/{{ patient.icn }}/notes/{{ note.id }}" class="btn btn-xs btn-outline">View Full</a>
                <button
                  class="btn btn-xs btn-danger"
                  hx-delete="/patients/{{ patient.icn }}/notes/{{ note.id }}"
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

  {# Back Button #}
  <div class="page-footer">
    <a href="/dashboard" class="btn btn-outline">
      <svg class="btn-icon-sm" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z"/>
      </svg>
      Back to Roster
    </a>
  </div>
</div>

{# Alpine.js for collapsible sections #}
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
{% endblock %}
```

### CSS Example (Patient Detail)

```css
/* static/css/patient_detail.css */

/* Patient Detail Container */
.patient-detail-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-6);
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

/* Empty State Hint */
.empty-hint {
  padding: var(--space-6);
  text-align: center;
  color: var(--gray-500);
  font-style: italic;
}

/* Page Footer */
.page-footer {
  margin-top: var(--space-8);
  padding-top: var(--space-6);
  border-top: 1px solid var(--gray-200);
}

/* Action Buttons Group */
.action-buttons {
  display: flex;
  gap: var(--space-2);
}

/* Helper Function (add to Python template context) */
/*
def calculate_age(birth_date):
    from datetime import date
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
*/
```

---

## 15.5 Add/Edit Patient Form

### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ med-z4 Simple EHR                                      [Logout] │
└─────────────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════════╗
║  Add New Patient                                [Cancel]      ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Personal Information                                         ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │ First Name: *                                           │  ║
║  │ [_______________________]                               │  ║
║  │                                                         │  ║
║  │ Last Name: *                                            │  ║
║  │ [_______________________]                               │  ║
║  │                                                         │  ║
║  │ Date of Birth: *                                        │  ║
║  │ [MM] / [DD] / [YYYY]                                    │  ║
║  │                                                         │  ║
║  │ Gender: *                                               │  ║
║  │ ○ Male   ○ Female   ○ Other                             │  ║
║  │                                                         │  ║
║  │ Social Security Number:                                 │  ║
║  │ [___] - [__] - [____]                                   │  ║
║  │ ℹ️  Optional. Will be masked in display.                │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                               ║
║  ℹ️  Fields marked with * are required                        ║
║                                                               ║
║  [Cancel]                                   [Save Patient]    ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

### Design Specifications

**Form Layout**:
- Two-column grid on desktop (single column on mobile)
- Labels above inputs (not inline) for accessibility
- Required field indicator: Red asterisk (*) next to label
- Help text: Light gray, italic, below input
- Field spacing: 24px vertical gap between fields

**Input Styles**:
- Text inputs: 100% width, 44px height, 14px padding
- Border: 2px solid gray-200, focus border teal-500
- Focus state: Teal border + subtle shadow
- Placeholder text: gray-400
- Error state: Red border + red text below

**Radio Buttons** (Gender):
- Horizontal layout with icons
- Large click targets (48px height)
- Custom styling (Teal accent when selected)
- Accessible labels

**SSN Input**:
- Three separate inputs with auto-tab on complete
- Formatted display (###-##-####)
- Info icon with tooltip explaining masking

**Validation**:
- Client-side: HTML5 required, pattern matching
- Server-side: FastAPI validation with Pydantic
- Error display: Below field, red text, icon
- Success: Green checkmark appears on valid input

**Buttons**:
- Primary (Save): Teal background, right-aligned
- Secondary (Cancel): Gray outline, left-aligned
- Loading state: Spinner replaces button text
- Disabled state: Gray background, no hover

### HTML/Jinja2 Template Example

```html
{# templates/patient_form.html #}
{% extends "base.html" %}

{% block title %}
  {% if patient %}Edit Patient{% else %}Add New Patient{% endif %} - med-z4
{% endblock %}

{% block content %}
<div class="form-container">
  <div class="card">
    <div class="card-header">
      <h2 class="card-title">
        {% if patient %}Edit Patient{% else %}Add New Patient{% endif %}
      </h2>
      <a href="{% if patient %}/patients/{{ patient.icn }}{% else %}/dashboard{% endif %}" class="btn btn-sm btn-ghost">
        Cancel
      </a>
    </div>

    <div class="card-body">
      <form
        method="POST"
        action="{% if patient %}/patients/{{ patient.icn }}/edit{% else %}/patients/new{% endif %}"
        class="patient-form"
        hx-post="{% if patient %}/patients/{{ patient.icn }}/edit{% else %}/patients/new{% endif %}"
        hx-target="#form-errors"
        hx-swap="innerHTML"
      >
        {# Error Summary (HTMX target for server validation errors) #}
        <div id="form-errors" class="error-summary" style="display: none;"></div>

        {# Personal Information Section #}
        <fieldset class="form-section">
          <legend class="section-legend">Personal Information</legend>

          <div class="form-grid">
            {# First Name #}
            <div class="form-group">
              <label for="first_name" class="form-label required">
                First Name
              </label>
              <input
                type="text"
                id="first_name"
                name="first_name"
                class="form-input"
                value="{{ patient.first_name if patient else '' }}"
                required
                maxlength="50"
                autofocus
                placeholder="Enter first name"
              >
              <span class="field-error" id="first_name-error"></span>
            </div>

            {# Last Name #}
            <div class="form-group">
              <label for="last_name" class="form-label required">
                Last Name
              </label>
              <input
                type="text"
                id="last_name"
                name="last_name"
                class="form-input"
                value="{{ patient.last_name if patient else '' }}"
                required
                maxlength="50"
                placeholder="Enter last name"
              >
              <span class="field-error" id="last_name-error"></span>
            </div>

            {# Date of Birth #}
            <div class="form-group">
              <label for="date_of_birth" class="form-label required">
                Date of Birth
              </label>
              <input
                type="date"
                id="date_of_birth"
                name="date_of_birth"
                class="form-input"
                value="{{ patient.date_of_birth.strftime('%Y-%m-%d') if patient else '' }}"
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
                  <input
                    type="radio"
                    name="gender"
                    value="M"
                    {% if patient and patient.gender == 'M' %}checked{% endif %}
                    required
                  >
                  <span class="radio-label">
                    <svg class="radio-icon" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"/>
                    </svg>
                    Male
                  </span>
                </label>

                <label class="radio-option">
                  <input
                    type="radio"
                    name="gender"
                    value="F"
                    {% if patient and patient.gender == 'F' %}checked{% endif %}
                    required
                  >
                  <span class="radio-label">
                    <svg class="radio-icon" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"/>
                    </svg>
                    Female
                  </span>
                </label>

                <label class="radio-option">
                  <input
                    type="radio"
                    name="gender"
                    value="O"
                    {% if patient and patient.gender == 'O' %}checked{% endif %}
                    required
                  >
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
            <div class="form-group full-width">
              <label for="ssn" class="form-label">
                Social Security Number
                <span class="optional-badge">Optional</span>
              </label>
              <input
                type="text"
                id="ssn"
                name="ssn"
                class="form-input"
                value="{{ patient.ssn if patient else '' }}"
                pattern="^\d{3}-\d{2}-\d{4}$"
                placeholder="###-##-####"
                maxlength="11"
              >
              <span class="field-help">
                <svg class="help-icon" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"/>
                </svg>
                SSN will be masked in display (only last 4 digits shown)
              </span>
              <span class="field-error" id="ssn-error"></span>
            </div>
          </div>
        </fieldset>

        {# Required Field Notice #}
        <div class="form-notice">
          <svg class="notice-icon" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"/>
          </svg>
          <span>Fields marked with <span class="required-indicator">*</span> are required</span>
        </div>

        {# Form Actions #}
        <div class="form-actions">
          <a href="{% if patient %}/patients/{{ patient.icn }}{% else %}/dashboard{% endif %}" class="btn btn-outline">
            <svg class="btn-icon-sm" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"/>
            </svg>
            Cancel
          </a>
          <button type="submit" class="btn btn-primary">
            <svg class="btn-icon-sm" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/>
            </svg>
            <span class="button-text">{% if patient %}Update{% else %}Save{% endif %} Patient</span>
            <span class="button-spinner" style="display: none;">
              <svg class="spinner" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" opacity="0.25"/>
                <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" opacity="0.75"/>
              </svg>
              Saving...
            </span>
          </button>
        </div>
      </form>
    </div>
  </div>
</div>

{# Client-side validation and SSN formatting #}
<script>
  // SSN auto-formatting
  document.getElementById('ssn').addEventListener('input', function(e) {
    let value = e.target.value.replace(/\D/g, '');
    if (value.length >= 3) value = value.slice(0,3) + '-' + value.slice(3);
    if (value.length >= 6) value = value.slice(0,6) + '-' + value.slice(6,10);
    e.target.value = value;
  });

  // Form submission with loading state
  document.querySelector('.patient-form').addEventListener('submit', function(e) {
    const button = e.target.querySelector('button[type="submit"]');
    button.disabled = true;
    button.querySelector('.button-text').style.display = 'none';
    button.querySelector('.button-spinner').style.display = 'inline-flex';
  });
</script>
{% endblock %}
```

### CSS Example (Forms)

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
  padding: var(--space-4);
  background-color: #fee2e2;
  border-left: 4px solid var(--danger-red);
  border-radius: 6px;
  margin-bottom: var(--space-6);
}

.error-summary:empty {
  display: none;
}

/* Form Notice */
.form-notice {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  background-color: #dbeafe;
  border-left: 4px solid var(--info-blue);
  border-radius: 6px;
  font-size: var(--text-sm);
  color: var(--gray-700);
  margin-bottom: var(--space-6);
}

.notice-icon {
  width: 20px;
  height: 20px;
  color: var(--info-blue);
  flex-shrink: 0;
}

.required-indicator {
  color: var(--danger-red);
  font-weight: bold;
  font-size: var(--text-base);
}

/* Form Actions */
.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-4);
  padding-top: var(--space-6);
  border-top: 2px solid var(--gray-200);
}

/* Button Spinner */
.button-spinner {
  display: none;
  align-items: center;
  gap: var(--space-2);
}

.spinner {
  width: 20px;
  height: 20px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Responsive Design */
@media (max-width: 640px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .radio-group {
    flex-direction: column;
  }

  .radio-option {
    width: 100%;
  }

  .form-actions {
    flex-direction: column-reverse;
  }

  .form-actions .btn {
    width: 100%;
  }
}
```

---

## 15.6 Add Vital Signs Form (Simplified CRUD Example)

### Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│ Add Vital Signs - Smith, Jane                      [Cancel] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Measurement Date/Time: *                                   │
│  [YYYY-MM-DD] [HH:MM]                                       │
│                                                             │
│  Blood Pressure:                                            │
│  Systolic: * [___] / Diastolic: * [___]  mmHg               │
│                                                             │
│  Heart Rate: *                                              │
│  [___] bpm                                                  │
│                                                             │
│  Temperature: *                                             │
│  [___] °F                                                   │
│                                                             │
│  Respiratory Rate:                                          │
│  [___] breaths/min                                          │
│                                                             │
│  Oxygen Saturation:                                         │
│  [___] %                                                    │
│                                                             │
│  [Cancel]                             [Save Vital Signs]    │
└─────────────────────────────────────────────────────────────┘
```

### HTML/Jinja2 Template Example (Abbreviated)

```html
{# templates/vital_form.html #}
{% extends "base.html" %}

{% block title %}Add Vital Signs - {{ patient.last_name }}, {{ patient.first_name }}{% endblock %}

{% block content %}
<div class="form-container">
  <div class="card">
    <div class="card-header">
      <h2 class="card-title">
        Add Vital Signs
        <span class="patient-context">{{ patient.last_name }}, {{ patient.first_name }}</span>
      </h2>
      <a href="/patients/{{ patient.icn }}" class="btn btn-sm btn-ghost">Cancel</a>
    </div>

    <div class="card-body">
      <form method="POST" action="/patients/{{ patient.icn }}/vitals/new" class="vitals-form">
        <div class="form-grid">
          {# Vital Date/Time #}
          <div class="form-group full-width">
            <label for="vital_date" class="form-label required">Measurement Date/Time</label>
            <div class="datetime-group">
              <input
                type="date"
                id="vital_date"
                name="vital_date"
                class="form-input"
                value="{{ today.strftime('%Y-%m-%d') }}"
                max="{{ today.strftime('%Y-%m-%d') }}"
                required
              >
              <input
                type="time"
                id="vital_time"
                name="vital_time"
                class="form-input"
                value="{{ now.strftime('%H:%M') }}"
                required
              >
            </div>
          </div>

          {# Blood Pressure #}
          <div class="form-group full-width">
            <label class="form-label">Blood Pressure</label>
            <div class="bp-group">
              <div class="bp-input-group">
                <label for="systolic" class="bp-label">Systolic *</label>
                <input
                  type="number"
                  id="systolic"
                  name="systolic"
                  class="form-input bp-input"
                  min="60"
                  max="250"
                  required
                  placeholder="120"
                >
              </div>
              <span class="bp-separator">/</span>
              <div class="bp-input-group">
                <label for="diastolic" class="bp-label">Diastolic *</label>
                <input
                  type="number"
                  id="diastolic"
                  name="diastolic"
                  class="form-input bp-input"
                  min="40"
                  max="150"
                  required
                  placeholder="80"
                >
              </div>
              <span class="unit-label">mmHg</span>
            </div>
          </div>

          {# Heart Rate #}
          <div class="form-group">
            <label for="heart_rate" class="form-label required">Heart Rate</label>
            <div class="input-with-unit">
              <input
                type="number"
                id="heart_rate"
                name="heart_rate"
                class="form-input"
                min="30"
                max="250"
                required
                placeholder="72"
              >
              <span class="unit-label">bpm</span>
            </div>
          </div>

          {# Temperature #}
          <div class="form-group">
            <label for="temperature" class="form-label required">Temperature</label>
            <div class="input-with-unit">
              <input
                type="number"
                id="temperature"
                name="temperature"
                class="form-input"
                min="95"
                max="108"
                step="0.1"
                required
                placeholder="98.6"
              >
              <span class="unit-label">°F</span>
            </div>
          </div>

          {# Respiratory Rate #}
          <div class="form-group">
            <label for="respiratory_rate" class="form-label">Respiratory Rate</label>
            <div class="input-with-unit">
              <input
                type="number"
                id="respiratory_rate"
                name="respiratory_rate"
                class="form-input"
                min="8"
                max="60"
                placeholder="16"
              >
              <span class="unit-label">breaths/min</span>
            </div>
          </div>

          {# Oxygen Saturation #}
          <div class="form-group">
            <label for="oxygen_saturation" class="form-label">Oxygen Saturation</label>
            <div class="input-with-unit">
              <input
                type="number"
                id="oxygen_saturation"
                name="oxygen_saturation"
                class="form-input"
                min="70"
                max="100"
                placeholder="98"
              >
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

### Additional CSS for Vital Forms

```css
/* static/css/forms.css (additional styles) */

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
```

---

## 15.7 HTMX Interaction Patterns

### Pattern 1: CCOW Context Polling

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
@app.get("/context/banner")
async def get_context_banner(session_id: str = Cookie(None)):
    active_patient = await get_active_ccow_patient(session_id)
    return templates.TemplateResponse(
        "partials/ccow_banner.html",
        {"request": request, "active_patient": active_patient}
    )
```

---

### Pattern 2: Set CCOW Context (No Page Refresh)

**Use Case**: Set CCOW context when user clicks "Set CCOW" button, refresh banner without full page reload.

**Implementation**:
```html
<button
  class="btn btn-sm btn-primary"
  hx-put="/context/set"
  hx-vals='{"icn": "{{ patient.icn }}"}'
  hx-swap="none"
  hx-on::after-request="if(event.detail.successful) { htmx.trigger('#ccow-banner', 'load'); }"
>
  Set CCOW
</button>
```

**Attributes**:
- `hx-put="/context/set"`: PUT request to set context
- `hx-vals='{"icn": "..."}'`: JSON payload with patient ICN
- `hx-swap="none"`: Don't replace button content
- `hx-on::after-request`: Custom JavaScript after request completes
- `htmx.trigger('#ccow-banner', 'load')`: Manually trigger banner refresh

**Backend Route**:
```python
@app.put("/context/set")
async def set_context(
    request: Request,
    session_id: str = Cookie(None)
):
    data = await request.json()
    icn = data.get("icn")

    # Call CCOW vault service
    ccow_client = CCOWClient(session_id)
    await ccow_client.set_context(icn)

    return {"success": True}
```

---

### Pattern 3: Delete with Confirmation and Animation

**Use Case**: Delete a vital sign record with confirmation dialog and fade-out animation.

**Implementation**:
```html
<button
  class="btn btn-xs btn-danger"
  hx-delete="/patients/{{ patient.icn }}/vitals/{{ vital.id }}"
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
- `hx-swap="outerHTML swap:1s"`: Replace element with 1-second fade-out

**Backend Route**:
```python
@app.delete("/patients/{icn}/vitals/{vital_id}")
async def delete_vital(
    icn: str,
    vital_id: int,
    session: AsyncSession = Depends(get_db_session)
):
    await session.execute(
        delete(PatientVital).where(PatientVital.id == vital_id)
    )
    await session.commit()

    # Return empty response (HTMX will remove element)
    return Response(status_code=200, content="")
```

---

### Pattern 4: Form Validation with Error Display

**Use Case**: Submit form via HTMX, display server-side validation errors inline.

**Implementation**:
```html
<form
  hx-post="/patients/new"
  hx-target="#form-errors"
  hx-swap="innerHTML"
>
  <div id="form-errors"></div>
  <!-- form fields -->
</form>
```

**Backend Route (Success)**:
```python
@app.post("/patients/new")
async def create_patient(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    # ... other fields
):
    # Validation passed, create patient
    patient = PatientDemographics(...)
    session.add(patient)
    await session.commit()

    # Redirect to patient detail page
    return RedirectResponse(
        url=f"/patients/{patient.icn}",
        status_code=303
    )
```

**Backend Route (Validation Error)**:
```python
@app.post("/patients/new")
async def create_patient(...):
    try:
        # Validation logic
        if not first_name:
            raise ValueError("First name is required")

        # ... create patient
    except ValueError as e:
        # Return error HTML fragment
        return templates.TemplateResponse(
            "partials/form_errors.html",
            {"request": request, "errors": [str(e)]}
        )
```

**Error Template**:
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

---

### Pattern 5: Out-of-Band Swaps (Multiple Updates)

**Use Case**: Update multiple page sections from a single HTMX request (e.g., update patient count AND table after creating new patient).

**Implementation**:
```html
<div id="patient-table" hx-target="this" hx-swap="outerHTML">
  <!-- table content -->
</div>

<div id="patient-count">
  Total: <span>4</span>
</div>
```

**Backend Route**:
```python
@app.post("/patients/new")
async def create_patient(...):
    # Create patient...

    # Return main content + OOB swap
    table_html = render_patient_table(patients)
    count_html = f'<div id="patient-count" hx-swap-oob="true">Total: <span>{len(patients)}</span></div>'

    return HTMLResponse(table_html + count_html)
```

**Learning Note**: `hx-swap-oob="true"` tells HTMX to update elements with matching IDs anywhere on the page, not just the target element.

---

## 15.8 Base Template and Layout

### HTML/Jinja2 Base Template

```html
{# templates/base.html #}
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}med-z4 Simple EHR{% endblock %}</title>

  {# CSS #}
  <link rel="stylesheet" href="/static/css/style.css">
  <link rel="stylesheet" href="/static/css/login.css">
  <link rel="stylesheet" href="/static/css/dashboard.css">
  <link rel="stylesheet" href="/static/css/patient_detail.css">
  <link rel="stylesheet" href="/static/css/forms.css">

  {# HTMX #}
  <script src="https://unpkg.com/htmx.org@1.9.10"></script>

  {# Alpine.js (for collapsible sections) #}
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>

  {% block extra_head %}{% endblock %}
</head>
<body>
  {# Header Navigation (only on authenticated pages) #}
  {% if current_user %}
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
        {# CCOW Status Badge #}
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
          {{ current_user.username }}
        </span>
        <a href="/logout" class="btn btn-sm btn-ghost">
          <svg class="btn-icon-sm" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M3 3a1 1 0 00-1 1v12a1 1 0 102 0V4a1 1 0 00-1-1zm10.293 9.293a1 1 0 001.414 1.414l3-3a1 1 0 000-1.414l-3-3a1 1 0 10-1.414 1.414L14.586 9H7a1 1 0 100 2h7.586l-1.293 1.293z"/>
          </svg>
          Logout
        </a>
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
    <p>&copy; 2026 med-z4 Simple EHR | Version 1.0 | CCOW Testing Tool</p>
  </footer>

  {% block extra_scripts %}{% endblock %}
</body>
</html>
```

### CSS for Base Layout

```css
/* static/css/style.css - Base Layout */

:root {
  /* Color Palette (Teal Theme) */
  --primary-teal: #14b8a6;
  --primary-teal-dark: #0f766e;
  --primary-teal-light: #5eead4;
  --success-green: #10b981;
  --warning-amber: #f59e0b;
  --danger-red: #ef4444;
  --info-blue: #3b82f6;
  --gray-50: #f9fafb;
  --gray-100: #f3f4f6;
  --gray-200: #e5e7eb;
  --gray-400: #9ca3af;
  --gray-500: #6b7280;
  --gray-600: #4b5563;
  --gray-700: #374151;
  --gray-900: #111827;
  --ccow-active: #14b8a6;
  --ccow-inactive: #9ca3af;

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

/* Reset and Base Styles */
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
  display: flex;
  flex-direction: column;
}

/* App Header */
.app-header {
  background: linear-gradient(90deg, var(--primary-teal-dark) 0%, var(--primary-teal) 100%);
  color: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  position: sticky;
  top: 0;
  z-index: 1000;
}

.header-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--space-4) var(--space-6);
}

.header-left,
.header-center,
.header-right {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

/* Logo */
.logo-link {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  text-decoration: none;
  color: white;
}

.logo-icon {
  width: 32px;
  height: 32px;
}

.logo-text {
  font-size: var(--text-xl);
  font-weight: bold;
}

.logo-subtitle {
  font-size: var(--text-sm);
  opacity: 0.9;
}

/* CCOW Status Badge */
.ccow-badge {
  padding: var(--space-2) var(--space-4);
  border-radius: 20px;
  font-size: var(--text-sm);
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.ccow-badge.ccow-active {
  background-color: rgba(16, 185, 129, 0.2);
  color: #d1fae5;
}

.ccow-badge.ccow-inactive {
  background-color: rgba(156, 163, 175, 0.2);
  color: #e5e7eb;
}

/* User Info */
.user-info {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
}

.user-icon {
  width: 20px;
  height: 20px;
}

/* Main Content */
.main-content {
  flex: 1;
  padding: var(--space-6);
}

/* Footer */
.app-footer {
  background-color: white;
  border-top: 1px solid var(--gray-200);
  padding: var(--space-4);
  text-align: center;
  font-size: var(--text-sm);
  color: var(--gray-500);
}
```

---

## 15.9 UI/UX Best Practices

### Accessibility (508 Compliance)

1. **Semantic HTML**:
   - Use `<button>` for actions, `<a>` for navigation
   - Proper heading hierarchy (`<h1>` → `<h2>` → `<h3>`)
   - `<label>` elements with `for` attribute for all form inputs

2. **Keyboard Navigation**:
   - All interactive elements accessible via Tab key
   - Visible focus states (teal outline)
   - Skip links for screen readers (optional Phase 2)

3. **Color Contrast**:
   - All text meets WCAG AA standards (4.5:1 for body text, 3:1 for large text)
   - Never rely on color alone (use icons + text)

4. **ARIA Attributes** (when needed):
   - `role="alert"` for error messages
   - `aria-label` for icon-only buttons
   - `aria-live="polite"` for CCOW status updates

### Performance Considerations

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

### Responsive Design

1. **Breakpoints**:
   - Mobile: < 640px (single column, stacked buttons)
   - Tablet: 640px - 1024px (2-column grid where appropriate)
   - Desktop: > 1024px (full layout)

2. **Mobile-Specific Adjustments**:
   - Larger touch targets (44px minimum)
   - Horizontal scroll for wide tables
   - Collapsible navigation (Phase 2)

### Error Handling UX

1. **Form Validation**:
   - Inline errors below fields (red text + icon)
   - Error summary at top of form (red border-left)
   - Preserve user input on validation failure

2. **Network Errors**:
   - HTMX error handling (show toast notification)
   - Retry button for failed requests
   - Offline indicator (future enhancement)

3. **Empty States**:
   - Friendly messages: "No patients yet. Click Add New Patient to get started."
   - Call-to-action button in empty state
   - Icon illustration for visual interest

---

## 15.10 Component Library Quick Reference

### Button Styles

```html
<!-- Primary Button (Teal) -->
<button class="btn btn-primary">Save</button>

<!-- Secondary/Outline Button -->
<button class="btn btn-outline">Cancel</button>

<!-- Danger Button (Red) -->
<button class="btn btn-danger">Delete</button>

<!-- Ghost Button (Transparent) -->
<button class="btn btn-ghost">Close</button>

<!-- Small Button -->
<button class="btn btn-sm btn-primary">Edit</button>

<!-- Extra Small Button -->
<button class="btn btn-xs btn-outline">View</button>

<!-- Block Button (Full Width) -->
<button class="btn btn-primary btn-block">Login</button>

<!-- Button with Icon -->
<button class="btn btn-primary">
  <svg class="btn-icon-sm" viewBox="0 0 20 20" fill="currentColor">
    <path d="..."/>
  </svg>
  <span>Add Patient</span>
</button>
```

### Card Component

```html
<div class="card">
  <div class="card-header">
    <h2 class="card-title">Card Title</h2>
    <button class="btn btn-sm btn-primary">Action</button>
  </div>
  <div class="card-body">
    <!-- Card content -->
  </div>
</div>
```

### Badge/Pill Component

```html
<span class="badge badge-neutral">Male</span>
<span class="severity-badge severity-severe">Severe</span>
<span class="count-badge">3</span>
```

### Alert/Notice Component

```html
<div class="alert alert-error">
  <svg class="alert-icon" viewBox="0 0 20 20" fill="currentColor">
    <path d="..."/>
  </svg>
  <span>Error message here</span>
</div>

<div class="info-panel">
  <svg class="info-icon" viewBox="0 0 20 20" fill="currentColor">
    <path d="..."/>
  </svg>
  <div class="info-content">
    <p class="info-title">Info Title</p>
    <p class="info-detail">Detail text</p>
  </div>
</div>
```

---

## 15.11 Learning Resources

### Understanding HTMX

**Key Concepts**:
- HTMX extends HTML with AJAX capabilities via attributes (`hx-get`, `hx-post`, `hx-put`, `hx-delete`)
- Server returns HTML fragments, not JSON (simplifies frontend)
- Supports out-of-band swaps for multi-element updates
- Event-driven interactions (`hx-trigger`, `hx-on`)

**Essential Reading**:
- HTMX Documentation: https://htmx.org/docs/
- HTMX Examples: https://htmx.org/examples/
- HTMX Book (free): "Hypermedia Systems" by Carson Gross

### Understanding Jinja2 Templates

**Key Concepts**:
- Template inheritance (`{% extends "base.html" %}`)
- Block overrides (`{% block content %}...{% endblock %}`)
- Variable substitution (`{{ variable }}` - auto-escaped)
- Control flow (`{% if %}`, `{% for %}`)
- Filters (`{{ date|strftime('%Y-%m-%d') }}`)

**Essential Reading**:
- Jinja2 Documentation: https://jinja.palletsprojects.com/
- FastAPI Template Guide: https://fastapi.tiangolo.com/advanced/templates/

### Understanding Alpine.js (Minimal JavaScript)

**Use Cases in med-z4**:
- Collapsible sections (`x-data`, `x-show`, `x-collapse`)
- Toggle states without server round-trip
- Lightweight alternative to React/Vue for simple interactions

**Essential Reading**:
- Alpine.js Documentation: https://alpinejs.dev/
- Alpine.js Start Here: https://alpinejs.dev/start-here

### CSS Layout Techniques

**Key Concepts**:
- CSS Grid for 2D layouts (form grids, card layouts)
- Flexbox for 1D layouts (button groups, navigation)
- CSS Custom Properties (variables) for theme consistency
- Media queries for responsive design

**Essential Reading**:
- CSS Grid Guide: https://css-tricks.com/snippets/css/complete-guide-grid/
- Flexbox Guide: https://css-tricks.com/snippets/css/a-guide-to-flexbox/

---

# 16. Implementation Mapping: Roadmap ↔ UI/UX

**START HERE:** This section is your primary implementation guide. It provides a clear mapping between the Implementation Roadmap (Section 10) and the UI/UX Design Specifications (Section 15), ensuring you know exactly which wireframes, templates, CSS, and backend routes to implement at each phase.

**Purpose:** When Section 10 says "Create \`templates/login.html\`", this section tells you to copy the complete template from Section 15.2, including all associated CSS, HTMX patterns, and backend routes.

---

### 16.1 Routes and Templates Contract

This table provides a complete reference for all HTTP endpoints, authentication requirements, inputs, outputs, and HTMX integration patterns.

#### Authentication Routes

| Route | Method | Auth Required | Inputs | Template/Response | HTMX | Error Behavior |
|-------|--------|---------------|--------|-------------------|------|----------------|
| `/login` | GET | No | None | `login.html` (full page) | No | N/A |
| `/login` | POST | No | Form: `username`, `password` | Redirect to `/dashboard` (success) or `login.html` with error | No | Display inline error message |
| `/logout` | POST | Yes | None | Redirect to `/login` | No | 401 if not authenticated |

#### Dashboard & Patient Roster Routes

| Route | Method | Auth Required | Inputs | Template/Response | HTMX | Error Behavior |
|-------|--------|---------------|--------|-------------------|------|----------------|
| `/dashboard` | GET | Yes | None | `dashboard.html` (full page) | Polls `/context/banner` every 5s | Redirect to `/login` if not authenticated |
| `/patients` | GET | Yes | None | Same as `/dashboard` (alias) | Same as dashboard | Same as dashboard |

#### CCOW Context Routes (HTMX Partials)

| Route | Method | Auth Required | Inputs | Template/Response | HTMX | Error Behavior |
|-------|--------|---------------|--------|-------------------|------|----------------|
| `/context/banner` | GET | Yes | None | `partials/ccow_banner.html` (partial) | **Yes** - Polled every 5s by dashboard | Return empty banner if session invalid |
| `/context/set` | PUT | Yes | JSON: `{"icn": "999V123456"}` | JSON: `{"success": true}` | **Yes** - Triggers banner refresh via `hx-on::after-request` | 400 if ICN invalid, 401 if not authenticated |
| `/context/clear` | DELETE | Yes | None | JSON: `{"success": true}` | **Yes** - Triggers banner refresh | 401 if not authenticated |
| `/context/debug` | GET | Yes | None | `partials/ccow_debug.html` (partial) | **Yes** - Polled every 5s (optional debug panel) | Return "Vault Offline" if unavailable |

#### Patient CRUD Routes

| Route | Method | Auth Required | Inputs | Template/Response | HTMX | Error Behavior |
|-------|--------|---------------|--------|-------------------|------|----------------|
| `/patients/new` | GET | Yes | None | `patient_form.html` (full page) | No | Redirect to `/login` if not authenticated |
| `/patients/new` | POST | Yes | Form: `first_name`, `last_name`, `date_of_birth`, `gender`, `ssn` (optional) | Redirect to `/patients/{icn}` (success) or return `partials/form_errors.html` (HTMX target) | **Optional** - Can use HTMX for inline validation | Display error summary at top of form |
| `/patients/{icn}` | GET | Yes | Path: `icn` | `patient_detail.html` (full page with vitals/allergies/notes) | Polls `/context/banner` every 5s | 404 if patient not found |
| `/patients/{icn}/edit` | GET | Yes | Path: `icn` | `patient_form.html` (pre-filled) | No | 404 if patient not found |
| `/patients/{icn}/edit` | POST | Yes | Path: `icn`, Form: (same as create) | Redirect to `/patients/{icn}` (success) or return errors | **Optional** - HTMX inline validation | 404 if patient not found, 400 for validation errors |
| `/patients/{icn}` | DELETE | Yes | Path: `icn` | 204 No Content | **Yes** - `hx-confirm` for confirmation, target: `body` (redirect) | 404 if patient not found, 403 if patient has clinical data |

#### Vital Signs CRUD Routes

| Route | Method | Auth Required | Inputs | Template/Response | HTMX | Error Behavior |
|-------|--------|---------------|--------|-------------------|------|----------------|
| `/patients/{icn}/vitals/new` | GET | Yes | Path: `icn` | `vital_form.html` (full page) | No | 404 if patient not found |
| `/patients/{icn}/vitals/new` | POST | Yes | Path: `icn`, Form: `vital_date`, `vital_time`, `systolic`, `diastolic`, `heart_rate`, `temperature`, `respiratory_rate`, `oxygen_saturation` | Redirect to `/patients/{icn}` (success) | No | 404 if patient not found, 400 for validation errors |
| `/patients/{icn}/vitals/{vital_id}/edit` | GET | Yes | Path: `icn`, `vital_id` | `vital_form.html` (pre-filled) | No | 404 if vital not found |
| `/patients/{icn}/vitals/{vital_id}/edit` | POST | Yes | Path: `icn`, `vital_id`, Form: (same as create) | Redirect to `/patients/{icn}` | No | 404 if vital not found |
| `/patients/{icn}/vitals/{vital_id}` | DELETE | Yes | Path: `icn`, `vital_id` | Empty response (200 OK) | **Yes** - `hx-confirm`, `hx-target="closest .vital-item"`, `hx-swap="outerHTML swap:1s"` (fade out) | 404 if vital not found |

#### Allergy CRUD Routes

| Route | Method | Auth Required | Inputs | Template/Response | HTMX | Error Behavior |
|-------|--------|---------------|--------|-------------------|------|----------------|
| `/patients/{icn}/allergies/new` | GET | Yes | Path: `icn` | `allergy_form.html` (full page) | No | 404 if patient not found |
| `/patients/{icn}/allergies/new` | POST | Yes | Path: `icn`, Form: `allergen`, `severity`, `reaction`, `observed_date` | Redirect to `/patients/{icn}` | No | 404 if patient not found, 400 for validation |
| `/patients/{icn}/allergies/{allergy_id}` | DELETE | Yes | Path: `icn`, `allergy_id` | Empty response (200 OK) | **Yes** - Same pattern as vitals delete | 404 if allergy not found |

#### Clinical Notes CRUD Routes

| Route | Method | Auth Required | Inputs | Template/Response | HTMX | Error Behavior |
|-------|--------|---------------|--------|-------------------|------|----------------|
| `/patients/{icn}/notes/new` | GET | Yes | Path: `icn` | `note_form.html` (full page) | No | 404 if patient not found |
| `/patients/{icn}/notes/new` | POST | Yes | Path: `icn`, Form: `note_type`, `note_date`, `author`, `note_text` | Redirect to `/patients/{icn}` | No | 404 if patient not found, 400 for validation |
| `/patients/{icn}/notes/{note_id}` | GET | Yes | Path: `icn`, `note_id` | `note_detail.html` (full page or modal) | No | 404 if note not found |
| `/patients/{icn}/notes/{note_id}` | DELETE | Yes | Path: `icn`, `note_id` | Empty response (200 OK) | **Yes** - Same pattern as vitals delete | 404 if note not found |

#### Health Check Routes

| Route | Method | Auth Required | Inputs | Template/Response | HTMX | Error Behavior |
|-------|--------|---------------|--------|-------------------|------|----------------|
| `/health` | GET | No | None | JSON: `{"status": "healthy", "database": "connected", "ccow_vault": "online"}` | No | N/A |
| `/` | GET | No | None | Redirect to `/dashboard` if authenticated, `/login` if not | No | N/A |

**HTMX Pattern Legend:**
- **Polling:** Automatic periodic GET requests (`hx-trigger="every 5s"`)
- **`hx-confirm`:** Browser confirmation dialog before request
- **`hx-target`:** DOM element to update (e.g., `#form-errors`, `closest .vital-item`)
- **`hx-swap`:** How to replace content (`outerHTML`, `innerHTML`, `none`, `outerHTML swap:1s` for animation)
- **`hx-on::after-request`:** JavaScript callback after request completes

---

**Purpose:** This guide provides a clear mapping between the Implementation Roadmap (Section 10) and the UI/UX Design Specifications (Section 15), ensuring you know exactly which wireframes, templates, and CSS to implement at each phase.

---

## Quick Reference: Phase → UI Components

| Phase | Tasks | Section 15 Reference | Files to Create |
|-------|-------|---------------------|-----------------|
| **Phase 2** | Authentication UI | 15.2 Login Screen | `templates/login.html`, `static/css/login.css` |
| **Phase 2** | Base Layout | 15.8 Base Template | `templates/base.html`, `static/css/style.css` |
| **Phase 3** | Patient Roster | 15.3 Dashboard Screen | `templates/dashboard.html`, `static/css/dashboard.css` |
| **Phase 3** | CCOW Banner | 15.3 Dashboard Screen | `templates/partials/ccow_banner.html` |
| **Phase 3** | HTMX Setup | 15.7 HTMX Patterns | Download HTMX library, implement polling pattern |
| **Phase 6** | Add Patient Form | 15.5 Add/Edit Patient Form | `templates/patient_form.html`, `static/css/forms.css` |
| **Phase 7** | Patient Detail | 15.4 Patient Detail Screen | `templates/patient_detail.html`, `static/css/patient_detail.css` |
| **Phase 7** | Vital Form | 15.6 Add Vital Signs Form | `templates/vital_form.html` (reuse forms.css) |
| **Phase 7** | Allergy/Note Forms | 15.5 + 15.6 patterns | Follow form patterns from 15.5/15.6 |
| **All Phases** | Components | 15.10 Component Library | Reusable button/card/badge HTML snippets |

---

## Phase-by-Phase Detailed Mapping

### Phase 1: Foundation (No UI Components)

**Section 10 Tasks:**
- Initialize repository
- Install dependencies
- Configure database

**No Section 15 References** - Backend setup only.

**Action Items:**
1. Create `requirements.txt` (from Section 4.2)
2. Create `config.py` (from Section 4.3)
3. Create `database.py` (from Section 5.3)

---

### Phase 2: Authentication

**Section 10 References:**
> 4. **Templates**
>    - Create `templates/base.html` (Teal theme layout)
>    - Create `templates/login.html` (password form)
>    - Add CSS in `static/css/style.css`

**Section 15 Mapping:**

| Section 10 Task | Section 15 Reference | What to Copy/Adapt |
|-----------------|---------------------|-------------------|
| Create `templates/base.html` | **15.8 Base Template** | Complete HTML template (lines 6315-6395), Base CSS (lines 6400-6562) |
| Create `templates/login.html` | **15.2 Login Screen** | Login template (lines 3727-3811), Login CSS (lines 3817-3974) |
| Teal theme CSS | **15.1 Design Philosophy** | CSS variables (lines 3610-3662) - copy to `style.css` |

**Step-by-Step Implementation:**

1. **Create Directory Structure:**
   ```bash
   mkdir -p templates/partials static/css static/js
   ```

2. **Create `static/css/style.css`** (Base Layout + Theme Variables):
   - Copy CSS variables from Section 15.1 (lines 3610-3662)
   - Copy base layout CSS from Section 15.8 (lines 6400-6562)
   - This is your foundation CSS file

3. **Create `templates/base.html`**:
   - Copy complete template from Section 15.8 (lines 6315-6395)
   - Pay attention to:
     - CSS link order (style.css must be first)
     - HTMX script include
     - Alpine.js script include (for collapsible sections)
     - `{% block content %}` for child templates

4. **Create `templates/login.html`**:
   - Copy complete template from Section 15.2 (lines 3727-3811)
   - Note the `{% extends "base.html" %}` pattern

5. **Create `static/css/login.css`**:
   - Copy all login CSS from Section 15.2 (lines 3817-3974)
   - Includes: login container, card, form styling, info panel

**Verification:**
- Visit http://localhost:8005/login
- Should see Teal gradient background
- Login card centered with shadow
- Form inputs have Teal focus border
- Info panel shows test credentials

**Common Mistakes to Avoid:**
- ❌ Don't forget to link CSS files in `base.html` header
- ❌ Don't miss CSS variable definitions (will break theme colors)
- ❌ Ensure static files are served (add `app.mount("/static", StaticFiles(directory="static"), name="static")` in `main.py`)

---

### Phase 3: Patient Roster & CCOW

**Section 10 References:**
> 5. **Templates**
>    - Create `templates/dashboard.html` (patient roster table)
>    - Create `templates/partials/active_patient_banner.html`
>    - Create `templates/partials/ccow_debug_panel.html`
>    - Add HTMX library to `static/js/`

**Section 15 Mapping:**

| Section 10 Task | Section 15 Reference | What to Copy/Adapt |
|-----------------|---------------------|-------------------|
| Create `templates/dashboard.html` | **15.3 Dashboard Screen** | Dashboard template (lines 4103-4222), Dashboard CSS (lines 4264-4538) |
| Create `partials/ccow_banner.html` | **15.3 Dashboard Screen** | CCOW banner partial (lines 4225-4258) |
| HTMX polling pattern | **15.7 Pattern 1** | CCOW polling code (lines 6083-6109) |
| Set CCOW button | **15.7 Pattern 2** | Set context code (lines 6115-6153) |

**Step-by-Step Implementation:**

1. **Download HTMX:**
   ```bash
   cd static/js
   curl -o htmx.min.js https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js
   ```
   Or use CDN in `base.html`: `<script src="https://unpkg.com/htmx.org@1.9.10"></script>`

2. **Create `static/css/dashboard.css`**:
   - Copy all dashboard CSS from Section 15.3 (lines 4264-4538)
   - Includes: card styling, table styling, CCOW banner, badges, empty states

3. **Create `templates/dashboard.html`**:
   - Copy complete template from Section 15.3 (lines 4103-4222)
   - **Key HTMX Patterns to Understand:**
     - `hx-get="/context/banner"` - Fetch banner HTML
     - `hx-trigger="load, every 5s"` - Poll every 5 seconds
     - `hx-swap="outerHTML"` - Replace entire element
     - `hx-put="/context/set"` - Set CCOW context
     - `hx-vals='{"icn": "..."}'` - Send JSON payload

4. **Create `templates/partials/ccow_banner.html`**:
   - Copy partial from Section 15.3 (lines 4225-4258)
   - This template renders two states: active vs. inactive

5. **Create Backend Routes** (not in Section 15, but required):
   ```python
   # app/routes/context.py
   from fastapi import APIRouter, Request, Depends
   from app.services.ccow_client import CCOWClient

   router = APIRouter()

   @router.get("/context/banner")
   async def get_banner(request: Request, current_user = Depends(get_current_user)):
       """HTMX partial: Render CCOW banner"""
       ccow = CCOWClient(request.cookies.get("med_z4_session_id"))
       active_patient = await ccow.get_context()

       return templates.TemplateResponse(
           "partials/ccow_banner.html",
           {"request": request, "active_patient": active_patient}
       )

   @router.put("/context/set")
   async def set_context(request: Request, current_user = Depends(get_current_user)):
       """Set CCOW context"""
       data = await request.json()
       icn = data.get("icn")

       ccow = CCOWClient(request.cookies.get("med_z4_session_id"))
       await ccow.set_context(icn)

       return {"success": True}
   ```

**Verification:**
- Dashboard shows patient table
- CCOW banner polls every 5 seconds (check network tab)
- Click "Set CCOW" → Banner updates without page reload
- Banner changes color (green = active, gray = inactive)

**HTMX Learning Path (Section 15.11):**
- Read HTMX docs: https://htmx.org/docs/
- Study Pattern 1 (Polling) in Section 15.7
- Study Pattern 2 (Set context) in Section 15.7

---

### Phase 4: CCOW Testing (No New UI)

**Section 10 Tasks:**
- Start both applications (med-z1 and med-z4)
- Test context synchronization
- Verify polling updates

**No New Section 15 References** - Testing phase only.

**Action Items:**
1. Follow test scenarios in Section 10 (lines 3074-3100)
2. Use CCOW debug panel to verify (already created in Phase 3)

---

### Phase 5: UI Polish

**Section 10 References:**
> 3. **Visual Polish**
>    - Refine Teal theme colors
>    - Add hover states to buttons
>    - Responsive layout (mobile-friendly table)

**Section 15 Mapping:**

| Section 10 Task | Section 15 Reference | What to Review/Refine |
|-----------------|---------------------|-----------------------|
| Hover states | **15.10 Component Library** | Button hover CSS already in templates |
| Responsive layout | **15.9 Responsive Design** | Media queries for mobile (lines 6607-6632) |
| Error handling UX | **15.9 Error Handling** | Empty states, error messages (lines 6618-6632) |

**Step-by-Step Implementation:**

1. **Add Loading Indicators:**
   ```html
   <!-- Add to buttons with HTMX actions -->
   <button
     class="btn btn-primary"
     hx-put="/context/set"
     hx-indicator="#spinner"
   >
     Set CCOW
     <span id="spinner" class="htmx-indicator">
       <svg class="spinner" ...>...</svg>
     </span>
   </button>
   ```

2. **Add Empty States** (already in Section 15.3 template):
   - Copy empty state HTML from Section 15.3 (lines 4204-4213)
   - CSS already included in dashboard.css

3. **Test Responsive Design:**
   - Open browser dev tools
   - Resize to mobile width (< 640px)
   - Verify table scrolls horizontally
   - Verify buttons stack vertically

**Verification:**
- All interactive elements show hover effects
- Loading spinners appear during HTMX requests
- Mobile layout doesn't break (tables scroll)

---

### Phase 6: Patient CRUD

**Section 10 References:**
> 3. **Templates**
>    - Create `templates/patient_create.html` (new patient form)
>    - Fields: name_first, name_last, dob, sex, ssn_last4, address

**Section 15 Mapping:**

| Section 10 Task | Section 15 Reference | What to Copy/Adapt |
|-----------------|---------------------|-------------------|
| Create patient form | **15.5 Add/Edit Patient Form** | Complete template (lines 5286-5512), Form CSS (lines 5517-5799) |
| Form validation | **15.7 Pattern 4** | Form validation with HTMX (lines 6245-6290) |
| Form styling | **15.5 Design Specs** | Field layout, radio buttons, error states (lines 5231-5283) |

**Step-by-Step Implementation:**

1. **Create `static/css/forms.css`**:
   - Copy all form CSS from Section 15.5 (lines 5517-5799)
   - Includes: form grid, input styling, radio buttons, error states

2. **Create `templates/patient_form.html`**:
   - Copy template from Section 15.5 (lines 5286-5512)
   - **Key Features:**
     - Form grid (2-column on desktop, 1-column mobile)
     - Required field indicators (red asterisk)
     - SSN auto-formatting JavaScript
     - Loading state for submit button
     - Error summary section (HTMX target)

3. **Review Wireframe:**
   - See Section 15.5 wireframe (lines 5208-5229) for visual layout
   - Understand field grouping (personal info section)

4. **Add Route (Backend):**
   ```python
   # app/routes/crud.py
   from fastapi import APIRouter, Form, Request
   from app.services.patient_service import generate_unique_icn

   router = APIRouter()

   @router.get("/patients/new")
   async def new_patient_form(request: Request):
       """Display new patient form"""
       return templates.TemplateResponse(
           "patient_form.html",
           {"request": request, "patient": None, "today": date.today()}
       )

   @router.post("/patients/new")
   async def create_patient(
       first_name: str = Form(...),
       last_name: str = Form(...),
       date_of_birth: date = Form(...),
       gender: str = Form(...),
       ssn: str | None = Form(None),
       db: AsyncSession = Depends(get_db_session)
   ):
       """Create new patient"""
       # Generate unique ICN
       icn = await generate_unique_icn(db)

       # Create patient record
       patient = PatientDemographics(
           icn=icn,
           patient_key=icn,  # Use ICN as patient_key for simplicity
           first_name=first_name,
           last_name=last_name,
           name_display=f"{last_name}, {first_name}",
           date_of_birth=date_of_birth,
           gender=gender,
           ssn=ssn,
           source_system="med-z4",
           last_updated=datetime.utcnow()
       )

       db.add(patient)
       await db.commit()
       await db.refresh(patient)

       return RedirectResponse(
           url=f"/patients/{patient.icn}",
           status_code=303
       )
   ```

**Verification:**
- Visit http://localhost:8005/patients/new
- Form displays with Teal theme
- Required fields marked with red asterisk
- SSN auto-formats as you type (###-##-####)
- Submit creates patient with 999V###### ICN
- Redirects to patient detail page

**Form Validation Learning (Section 15.7):**
- Study Pattern 4 (lines 6245-6290)
- Understand `hx-target="#form-errors"` for error display
- Learn how to return HTML error fragments from backend

---

### Phase 7: Clinical Data CRUD

**Section 10 References:**
> 3. **Templates**
>    - Create `templates/partials/forms/vital_form.html`
>    - Create `templates/partials/forms/allergy_form.html`
>    - Create `templates/partials/forms/note_form.html`
>
> 4. **Patient Detail Page**
>    - Create `GET /patients/{icn}` route
>    - Create `templates/patient_detail.html`
>    - Display patient info + tabs for vitals, allergies, notes

**Section 15 Mapping:**

| Section 10 Task | Section 15 Reference | What to Copy/Adapt |
|-----------------|---------------------|-------------------|
| Patient detail page | **15.4 Patient Detail Screen** | Template (lines 4628-4887), CSS (lines 4893-5203) |
| Vital signs form | **15.6 Add Vital Signs Form** | Template (lines 5836-5993), CSS (lines 5999-6076) |
| Collapsible sections | **15.4 Design Specs** | Alpine.js pattern (lines 4661-4887) |
| Delete with animation | **15.7 Pattern 3** | HTMX delete pattern (lines 6159-6191) |

**Step-by-Step Implementation:**

1. **Create `static/css/patient_detail.css`**:
   - Copy all CSS from Section 15.4 (lines 4893-5203)
   - Includes: detail list, clinical sections, vitals/allergies/notes styling

2. **Create `templates/patient_detail.html`**:
   - Copy template from Section 15.4 (lines 4628-4887)
   - **Key Features:**
     - Collapsible clinical sections (using Alpine.js)
     - HTMX polling for CCOW banner
     - "Set as CCOW" button
     - Empty states for each domain
     - Delete buttons with confirmation

3. **Review Wireframe:**
   - See Section 15.4 wireframe (lines 4543-4577) for visual layout
   - Understand section organization (Demographics → Vitals → Allergies → Notes)

4. **Create `templates/vital_form.html`**:
   - Copy template from Section 15.6 (lines 5836-5993)
   - Copy additional vital CSS from Section 15.6 (lines 5999-6076)
   - **Key Features:**
     - Blood pressure (systolic/diastolic) input group
     - Units displayed next to inputs (bpm, °F, mmHg)
     - DateTime picker for measurement time
     - Number inputs with min/max validation

5. **Create Allergy & Note Forms** (Pattern from 15.5 + 15.6):
   - Follow the same form structure as patient form (15.5)
   - Use the datetime/unit patterns from vital form (15.6)
   - **Allergy Form Fields:**
     - Allergen name (text input)
     - Severity (radio: Mild, Moderate, Severe)
     - Reaction description (textarea)
     - Observed date (date picker)
   - **Note Form Fields:**
     - Note type (select: Progress Note, Consult, Discharge Summary)
     - Note date (date picker)
     - Author (text input, default to current user)
     - Note text (textarea, large)

6. **Add Routes (Backend):**
   ```python
   # app/routes/crud.py (add to existing file)

   @router.get("/patients/{icn}")
   async def patient_detail(
       icn: str,
       request: Request,
       db: AsyncSession = Depends(get_db_session)
   ):
       """Display patient detail page with all clinical data"""
       # Query patient
       patient = await db.execute(
           select(PatientDemographics).where(PatientDemographics.icn == icn)
       )
       patient = patient.scalar_one_or_none()

       if not patient:
           raise HTTPException(404, "Patient not found")

       # Query vitals
       vitals = await db.execute(
           select(PatientVital)
           .where(PatientVital.icn == icn)
           .order_by(PatientVital.vital_date.desc())
           .limit(10)
       )
       vitals = vitals.scalars().all()

       # Query allergies
       allergies = await db.execute(
           select(PatientAllergy)
           .where(PatientAllergy.icn == icn)
           .order_by(PatientAllergy.observed_date.desc())
       )
       allergies = allergies.scalars().all()

       # Query notes
       notes = await db.execute(
           select(ClinicalNote)
           .where(ClinicalNote.icn == icn)
           .order_by(ClinicalNote.note_date.desc())
           .limit(10)
       )
       notes = notes.scalars().all()

       return templates.TemplateResponse(
           "patient_detail.html",
           {
               "request": request,
               "patient": patient,
               "vitals": vitals,
               "allergies": allergies,
               "notes": notes
           }
       )

   @router.get("/patients/{icn}/vitals/new")
   async def new_vital_form(icn: str, request: Request, db: AsyncSession = Depends(get_db_session)):
       """Display add vital form"""
       patient = await db.execute(
           select(PatientDemographics).where(PatientDemographics.icn == icn)
       )
       patient = patient.scalar_one_or_none()

       return templates.TemplateResponse(
           "vital_form.html",
           {
               "request": request,
               "patient": patient,
               "today": date.today(),
               "now": datetime.now()
           }
       )

   @router.post("/patients/{icn}/vitals/new")
   async def create_vital(
       icn: str,
       vital_date: date = Form(...),
       vital_time: str = Form(...),
       systolic: int = Form(...),
       diastolic: int = Form(...),
       heart_rate: int = Form(...),
       temperature: float = Form(...),
       respiratory_rate: int | None = Form(None),
       oxygen_saturation: int | None = Form(None),
       db: AsyncSession = Depends(get_db_session)
   ):
       """Create new vital sign record"""
       # Combine date and time
       vital_datetime = datetime.combine(vital_date, datetime.strptime(vital_time, "%H:%M").time())

       vital = PatientVital(
           icn=icn,
           vital_date=vital_datetime,
           systolic=systolic,
           diastolic=diastolic,
           heart_rate=heart_rate,
           temperature=temperature,
           respiratory_rate=respiratory_rate,
           oxygen_saturation=oxygen_saturation,
           source_system="med-z4",
           last_updated=datetime.utcnow()
       )

       db.add(vital)
       await db.commit()

       return RedirectResponse(
           url=f"/patients/{icn}",
           status_code=303
       )

   @router.delete("/patients/{icn}/vitals/{vital_id}")
   async def delete_vital(
       icn: str,
       vital_id: int,
       db: AsyncSession = Depends(get_db_session)
   ):
       """Delete vital sign record (HTMX)"""
       await db.execute(
           delete(PatientVital).where(PatientVital.id == vital_id)
       )
       await db.commit()

       # Return empty response (HTMX removes element)
       return Response(status_code=200, content="")
   ```

**Verification:**
- Visit http://localhost:8005/patients/999V123456
- See patient demographics card at top
- Clinical sections are collapsible (click chevron icon)
- Click "Add Vital" → Opens vital form
- Submit vital → Redirects to patient detail, vital appears in list
- Click "Delete" → Confirmation dialog, then fade-out animation (1 second)
- Verify data appears in med-z1 (open med-z1, search for patient)

**HTMX Delete Pattern (Section 15.7):**
- Study Pattern 3 (lines 6159-6191)
- Understand `hx-confirm` for browser confirmation
- Understand `hx-target="closest .vital-item"` for targeting parent element
- Understand `hx-swap="outerHTML swap:1s"` for fade-out animation

**Alpine.js Collapsible Pattern:**
- Study Section 15.4 template (lines 4661-4687)
- `x-data="{ open: true }"` - Component state
- `@click="open = !open"` - Toggle state on click
- `x-show="open"` - Conditional display
- `x-collapse` - Smooth collapse animation

---

### Phase 8: Documentation (No New UI)

**Section 10 Tasks:**
- Finalize README
- Add API documentation
- Code cleanup

**No New Section 15 References** - Documentation phase.

**Action Items:**
1. Use `/docs` endpoint (FastAPI automatic docs)
2. Add screenshots of UI to README
3. Reference Section 15 in README for UI design decisions

---

## Additional Practical Guidance

### Helper Functions Not in Section 15

These utility functions are referenced in templates but need to be defined in your backend:

```python
# app/utils/template_helpers.py

from datetime import date

def calculate_age(birth_date: date) -> int:
    """Calculate age from birth date"""
    today = date.today()
    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )

def format_ssn(ssn: str) -> str:
    """Mask SSN to show only last 4 digits"""
    if not ssn or len(ssn) < 4:
        return "***-**-****"
    return f"***-**-{ssn[-4:]}"

# Add to Jinja2 environment in main.py:
from app.utils.template_helpers import calculate_age, format_ssn

templates.env.globals['calculate_age'] = calculate_age
templates.env.globals['format_ssn'] = format_ssn
```

### Static Files Setup (Critical!)

```python
# main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="med-z4 Simple EHR")

# Mount static files BEFORE routes
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Add template helpers
from app.utils.template_helpers import calculate_age, format_ssn
templates.env.globals['calculate_age'] = calculate_age
templates.env.globals['format_ssn'] = format_ssn

# Include routers
from app.routes import auth, dashboard, context, crud
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(context.router, prefix="/context")
app.include_router(crud.router, prefix="/patients")
```

### Component Reuse Pattern

Instead of copy-pasting HTML, create reusable partials:

```html
{# templates/partials/button.html #}
{% macro button(text, type="button", class="btn-primary", icon=None, hx_attrs={}) %}
<button type="{{ type }}" class="btn {{ class }}"
  {% for attr, value in hx_attrs.items() %}
    {{ attr }}="{{ value }}"
  {% endfor %}
>
  {% if icon %}
    <svg class="btn-icon-sm" viewBox="0 0 20 20" fill="currentColor">
      <path d="{{ icon }}"/>
    </svg>
  {% endif %}
  <span>{{ text }}</span>
</button>
{% endmacro %}

{# Usage in other templates: #}
{% from "partials/button.html" import button %}
{{ button("Save Patient", type="submit", class="btn-primary") }}
```

### CSS Organization Checklist

Ensure all CSS files are created and linked:

```
static/css/
├── style.css          # Base layout + CSS variables (15.1 + 15.8)
├── login.css          # Login page (15.2)
├── dashboard.css      # Dashboard/roster (15.3)
├── patient_detail.css # Patient detail page (15.4)
└── forms.css          # All forms (15.5 + 15.6)
```

Link order in `base.html`:
```html
<link rel="stylesheet" href="/static/css/style.css">        <!-- Always first -->
<link rel="stylesheet" href="/static/css/login.css">
<link rel="stylesheet" href="/static/css/dashboard.css">
<link rel="stylesheet" href="/static/css/patient_detail.css">
<link rel="stylesheet" href="/static/css/forms.css">
```

---

## Learning Resources by Phase

### Phase 2 Learning:
- **Jinja2 Template Inheritance:** Section 15.11 → https://jinja.palletsprojects.com/
- **CSS Variables:** Section 15.1 (lines 3610-3662)
- **Gradient Backgrounds:** Section 15.2 CSS (lines 3819-3827)

### Phase 3 Learning:
- **HTMX Polling:** Section 15.7 Pattern 1 + https://htmx.org/docs/#polling
- **HTMX Attributes:** Section 15.7 + https://htmx.org/attributes/
- **CSS Grid for Tables:** Section 15.11 → https://css-tricks.com/snippets/css/complete-guide-grid/

### Phase 6-7 Learning:
- **Form Validation:** Section 15.7 Pattern 4
- **HTMX Form Submission:** https://htmx.org/examples/update-other-content/
- **Alpine.js Basics:** Section 15.11 → https://alpinejs.dev/start-here
- **CSS Flexbox for Forms:** Section 15.11 → https://css-tricks.com/snippets/css/a-guide-to-flexbox/

---

## Troubleshooting UI Issues

### Issue: CSS Not Loading

**Symptoms:** Page displays but no Teal theme, plain HTML
**Solution:**
1. Check static files are mounted: `app.mount("/static", ...)`
2. Verify CSS files exist in `static/css/` directory
3. Check browser Network tab for 404 errors
4. Ensure paths start with `/static/` not `static/`

### Issue: HTMX Not Working

**Symptoms:** Buttons don't do anything, no polling
**Solution:**
1. Check HTMX script is included in `<head>` of `base.html`
2. Open browser console, look for JavaScript errors
3. Check Network tab - should see XHR requests every 5 seconds
4. Verify backend routes return HTML, not JSON

### Issue: Alpine.js Not Working

**Symptoms:** Collapsible sections don't collapse
**Solution:**
1. Check Alpine.js script is included: `<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>`
2. Script must have `defer` attribute
3. Check `x-data` is on parent element
4. Verify syntax: `@click="open = !open"` not `@click="open = !open;"`

### Issue: Forms Not Submitting

**Symptoms:** Click submit, nothing happens
**Solution:**
1. Check form has `method="POST"` and `action="/path"`
2. Verify route accepts POST: `@router.post("/patients/new")`
3. Check CSRF token if using middleware (med-z4 doesn't use CSRF in spec)
4. Look at browser console for errors
5. Check backend logs for validation errors

---

**End of Implementation Mapping Guide**
