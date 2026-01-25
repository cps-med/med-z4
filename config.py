# -----------------------------------------------------------------
# config.py
# -----------------------------------------------------------------
# Centralized configuration for med-z4,using Pydantic
# -----------------------------------------------------------------

from pydantic_settings import BaseSettings, SettingsConfigDict

# Application Settings
class AppSettings(BaseSettings):
    name: str = "med-z4 (config)"
    version: str = "0.1.0 (config)"
    port: int = 8005
    debug: bool = True

    # Pydantic will look for APP_NAME, APP_VERSION, etc.
    model_config = SettingsConfigDict(env_file=".env", env_prefix='APP_', extra="ignore")


# Sample Endpoint Settions
class SampleSettings(BaseSettings):
    api_url: str = "https://jsonplaceholder.typicode.com"

    # Pydantic will look for SAMPLE_API_URL
    model_config = SettingsConfigDict(env_file=".env", env_prefix='SAMPLE_', extra="ignore")


# Session Management Settings
class SessionSettings(BaseSettings):
    secret_key: str
    timeout_minutes: int = 25
    cookie_name: str = 'med_z4_session_id'
    cookie_max_age: int = timeout_minutes * 60 

    # Pydantic will look for SESSION_SECRET_KEY, SESSION_TIMEOUT_MINUTES, etc.
    model_config = SettingsConfigDict(env_file=".env", env_prefix='SESSION_', extra="ignore")


# Main Settings container
class Settings(BaseSettings):
    app: AppSettings = AppSettings()
    sample: SampleSettings = SampleSettings()
    session: SessionSettings = SessionSettings()

# Instantiate the settings once to be imported elsewhere
settings = Settings()


# **** OLD CONFIG INFO BELOW ****

# Database Configuration
# ---------------------------------------------------------------------
# POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
# POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
# POSTGRES_DB = os.getenv("POSTGRES_DB", "medz1")
# POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
# POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

# if not POSTGRES_PASSWORD:
#     raise ValueError("POSTGRES_PASSWORD must be set in .env file")

# # SQLAlchemy async connection string
# DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# CCOW Configuration
# ---------------------------------------------------------------------
# CCOW_BASE_URL = os.getenv("CCOW_BASE_URL", "http://localhost:8001")

# Security Configuration
# ---------------------------------------------------------------------
# BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))

# Logging Configuration
# ---------------------------------------------------------------------
# LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
