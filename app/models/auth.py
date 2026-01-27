# -----------------------------------------------------------
# app/models/auth.py
# -----------------------------------------------------------
# SQLAlchemy models for authentication tables
# -----------------------------------------------------------

from sqlalchemy import Column, String, Integer, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class User(Base):
    """User model (auth.users table)."""
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    home_site_sta3n = Column(Integer)
    is_active = Column(Boolean, default=True)
    is_locked = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    last_login_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), default="system")


class Session(Base):
    """Session model (auth.sessions table)."""
    __tablename__ = "sessions"
    __table_args__ = {"schema": "auth"}

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.user_id"), nullable=False, index=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    last_activity_at = Column(TIMESTAMP, default=datetime.utcnow)
    expires_at = Column(TIMESTAMP, nullable=False)
    is_active = Column(Boolean, default=True)
    ip_address = Column(String(45))
    user_agent = Column(String(500))


class AuditLog(Base):
    """Audit log model (auth.audit_logs table)."""
    __tablename__ = "audit_logs"
    __table_args__ = {"schema": "auth"}

    audit_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.user_id", ondelete="SET NULL"))
    event_type = Column(String(50), nullable=False)
    event_timestamp = Column(TIMESTAMP, default=datetime.utcnow)
    email = Column(String(255))
    ip_address = Column(String(45))
    user_agent = Column(String)
    success = Column(Boolean)
    failure_reason = Column(String)
    session_id = Column(UUID(as_uuid=True))