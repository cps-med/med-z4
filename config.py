# -----------------------------------------------------------------
# config.py
# -----------------------------------------------------------------
# Centralized configuration for med-z4,using Pydantic
# -----------------------------------------------------------------

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Application Settings
class AppSettings(BaseSettings):
    name: str = "med-z4 (config.py)"
    version: str = "0.1.0 (config.py)"
    port: int = 8005
    debug: bool = True

    # Pydantic will look for APP_NAME, APP_VERSION, etc.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix='APP_',
        extra="ignore"
    )


# Sample Endpoint Settions (for testing external API calls)
class SampleSettings(BaseSettings):
    api_url: str = "https://jsonplaceholder.typicode.com"

    # Pydantic will look for SAMPLE_API_URL
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix='SAMPLE_',
        extra="ignore"
    )


# Session Management Settings
class SessionSettings(BaseSettings):
    secret_key: str
    timeout_minutes: int = 25
    cookie_name: str = 'med_z4_session_id'

    # Pydantic will look for SESSION_SECRET_KEY, SESSION_TIMEOUT_MINUTES, etc.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix='SESSION_',
        extra="ignore"
    )

    @property
    def cookie_max_age(self) -> int:
        """Computed property: converts timeout_minutes to seconds"""
        return self.timeout_minutes * 60
    
    @field_validator("secret_key")
    @classmethod
    def validate_secret_key_length(cls, v: str) -> str:
        """Validator: ensure secret key is at least 32 characters"""
        if len(v) < 32:
            raise ValueError("SESSION_SECRET_KEY must be at least 32 characters")
        return v


# CCOW Context Vault Settings
class CCOWSettings(BaseSettings):
    base_url: str
    health_endpoint: str

    # Pydantic will look for CCOW_BASE_URL, CCOW_HEALTH_ENDPOINT, etc.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix='CCOW_',
        extra="ignore"
    )


# VistA Real-time Service
class VistaSettings(BaseSettings):
    base_url: str
    health_endpoint: str

    # Pydantic will look for VISTA_BASE_URL, VISTA_HEALTH_ENDPOINT, etc.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix='VISTA_',
        extra="ignore"
    )


# PostgreSQL Database Settings (to be implemented)
class PostgresSettings(BaseSettings):
    """
    Database configuration using Pydantic Settings.
    To be implemented in upcoming development phase.

    Will include:
    - host, port, db, user, password fields
    - Validator for required password
    - Computed property for DATABASE_URL connection string
    """
    host: str = "localhost"
    port: int = 5432
    db: str = "medz1"
    user: str = "postgres"
    password: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="POSTGRES_",
        extra="ignore"
    )

    @property
    def database_url(self) -> str:
        """Computed property: SQLAlchemy async connection string"""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    @field_validator("password")
    @classmethod
    def validate_password_required(cls, v: str) -> str:
        """Validator: Ensure password is provided"""
        if not v:
            raise ValueError("POSTGRES_PASSWORD must be set in .env file")
        return v


# Main Settings Container
class Settings(BaseSettings):
    """
    Main settings container that groups all configuration classes.
    Import this single object in application code.
    """
    app: AppSettings = AppSettings()
    sample: SampleSettings = SampleSettings()
    session: SessionSettings = SessionSettings()
    ccow: CCOWSettings = CCOWSettings()
    vista: VistaSettings = VistaSettings()
    postgres: PostgresSettings = PostgresSettings()


# Instantiate the settings once to be imported elsewhere
settings = Settings()


# **** OLD CONFIG INFO BELOW (not sure if still needed) ****

# # SQLAlchemy async connection string
# DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Security Configuration
# ---------------------------------------------------------------------
# BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))

# Logging Configuration
# ---------------------------------------------------------------------
# LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
