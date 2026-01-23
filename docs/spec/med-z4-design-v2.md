# med-z4 (Simple EHR) – Design Specification

**Document Version:** v2.0 (Restructured)  
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
6. [Authentication Design](#6-authentication-design)
7. [CCOW Context Management](#7-ccow-context-management)
8. [Core Features (Phase 1-5)](#8-core-features-phase-1-5)
9. [Clinical Data Management (CRUD) - Phase 6-8](#9-clinical-data-management-crud---phase-6-8)
10. [Implementation Roadmap](#10-implementation-roadmap)
11. [UI/UX Design & Wireframes](#11-uiux-design--wireframes)
12. [Testing Strategy](#12-testing-strategy)
13. [Known Limitations & Future Enhancements](#13-known-limitations--future-enhancements)
14. [Deployment Considerations](#14-deployment-considerations)
15. [References](#15-references)
16. [Glossary](#16-glossary)

**Appendices:**
- [Appendix A: Quick Reference Commands](#appendix-a-quick-reference-commands)
- [Appendix B: Troubleshooting Guide](#appendix-b-troubleshooting-guide)
- [Appendix C: Template Variable Reference](#appendix-c-template-variable-reference)

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

### 2.4 Async vs Sync Decision

**This specification uses async SQLAlchemy patterns** for consistency with modern FastAPI best practices:

```python
# ✅ Standard pattern used throughout this specification
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

async def get_patient(db: AsyncSession, icn: str):
    result = await db.execute(
        select(PatientDemographics).where(PatientDemographics.patient_key == icn)
    )
    return result.scalar_one_or_none()
```

**Rationale:**
- Async patterns handle concurrent requests more efficiently
- Better alignment with FastAPI's async-first design
- Consistent with CCOW client operations (httpx async)

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
│   │   ├── patient_service.py          # Patient data operations (Phase 6+)
│   │   └── audit_service.py            # Clinical audit logging
│   │
│   └── middleware/                     # Custom middleware (if needed)
│       └── __init__.py
│
├── templates/                          # Jinja2 HTML templates
│   ├── base.html                       # Base layout with Teal theme
│   ├── login.html                      # Login form with password input
│   ├── dashboard.html                  # Patient roster table
│   ├── patient_form.html               # New/edit patient form (Phase 6+)
│   ├── patient_detail.html             # Patient detail page with tabs (Phase 6+)
│   │
│   └── partials/                       # HTMX partial templates (fragments)
│       ├── patient_row.html            # Single patient table row
│       ├── ccow_banner.html            # Top banner with active patient
│       ├── ccow_debug_panel.html       # CCOW status widget
│       └── forms/                      # Reusable form components (Phase 6+)
│           ├── vital_form.html
│           ├── allergy_form.html
│           └── note_form.html
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

**Purpose:** Show CCOW vault status and context details for debugging during development.

**Route:** `GET /context/debug` (HTMX partial)

**Implementation:** See Section 11.10 (Component Library) for template and CSS.

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

### 11.7 HTMX Patterns

**Pattern 1: Polling for Context Updates**
```html
<div id="ccow-banner"
     hx-get="/context/banner"
     hx-trigger="load, every 5s"
     hx-swap="outerHTML">
```

**Pattern 2: Button Click with Response Swap**
```html
<button hx-post="/context/set/{{ patient.icn }}"
        hx-swap="none"
        hx-on::after-request="htmx.trigger('#ccow-banner', 'load')">
    Select
</button>
```

**Pattern 3: Delete with Confirmation**
```html
<button hx-delete="/patients/{{ icn }}/vitals/{{ vital.vital_id }}"
        hx-confirm="Delete this vital?"
        hx-target="closest .vital-item"
        hx-swap="outerHTML swap:1s">
    Delete
</button>
```

### 11.8 Base Template

**Template (templates/base.html):**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}med-z4{% endblock %}</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="stylesheet" href="/static/css/login.css">
    <link rel="stylesheet" href="/static/css/dashboard.css">
    <link rel="stylesheet" href="/static/css/patient_detail.css">
    <link rel="stylesheet" href="/static/css/forms.css">
    <script src="/static/js/htmx.min.js"></script>
</head>
<body>
    {% if user %}
    <header class="app-header">
        <div class="header-container">
            <div class="header-left">
                <a href="/dashboard" class="logo-link">
                    <span class="logo-text">med-z4</span>
                    <span class="logo-subtitle">Simple EHR</span>
                </a>
            </div>
            <div class="header-right">
                <span class="user-info">{{ user.display_name }}</span>
                <form action="/logout" method="POST" style="display: inline;">
                    <button type="submit" class="btn btn-sm">Logout</button>
                </form>
            </div>
        </div>
    </header>
    {% endif %}

    <main class="main-content">
        {% block content %}{% endblock %}
    </main>

    <footer class="app-footer">
        <p>med-z4 Simple EHR | CCOW Testing Application</p>
    </footer>
</body>
</html>
```

### 11.9 Accessibility (508 Compliance)

1. **Semantic HTML:** Use `<button>` for actions, `<a>` for navigation
2. **Keyboard Navigation:** All interactive elements accessible via Tab
3. **Color Contrast:** WCAG AA standards (4.5:1 for body text)
4. **ARIA Attributes:** `role="alert"` for errors, `aria-live="polite"` for CCOW updates

### 11.10 Component Library

Reusable components available:
- Buttons (`.btn`, `.btn-primary`, `.btn-sm`, `.btn-danger`)
- Alerts (`.alert`, `.alert-error`, `.alert-success`)
- Form controls (`.form-group`, `.form-input`)
- Cards and panels
- Tables with striped rows
- CCOW banner and debug panel

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

---

**End of Design Specification**
