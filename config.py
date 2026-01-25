# -----------------------------------------------------------------
# config.py
# -----------------------------------------------------------------
# Centralized configuration for med-z4
# Reads from .env file and provides typed config objects
# -----------------------------------------------------------------
# Usage:
#    from config import (
#        PROJECT_ROOT,
#        CDWWORK_DB_CONFIG,
#        CDWWORK2_DB_CONFIG,
#        EXTRACT_DB_CONFIG,
#        MINIO_CONFIG,
#        PATHS,
#        USE_MINIO,
#    )
# -----------------------------------------------------------------

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