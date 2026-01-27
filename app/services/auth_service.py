# -----------------------------------------------------------
# app/services/auth_service.py
# -----------------------------------------------------------
# Authentication service functions
# -----------------------------------------------------------

import bcrypt
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import logging

from app.models.auth import User, Session as SessionModel, AuditLog
from config import settings

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
        logger.warning(f"Authentication failed: user not found - {email}")
        return None

    if user.is_locked:
        logger.warning(f"Authentication failed: account locked - {email}")
        return None

    if not user.is_active:
        logger.warning(f"Authentication failed: user inactive - {email}")
        return None

    # Verify password
    if not verify_password(password, user.password_hash):
        logger.warning(f"Authentication failed: invalid password - {email}")
        # Increment failed login attempts
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.is_locked = True
            logger.warning(f"Account locked after 5 failed attempts: {email}")
        await db.commit()
        return None

    # Reset failed login attempts on successful login
    await db.execute(
        update(User)
        .where(User.user_id == user.user_id)
        .values(
            last_login_at=datetime.utcnow(),
            failed_login_attempts=0
        )
    )
    await db.commit()

    logger.info(f"Authentication successful: {email}")
    return user


async def create_session(
    db: AsyncSession,
    user: User,
    ip_address: str,
    user_agent: str
) -> Dict[str, Any]:
    """Create a new session for authenticated user."""
    session_id = uuid.uuid4()
    expires_at = datetime.utcnow() + timedelta(minutes=settings.session.timeout_minutes)

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

    logger.info(f"Session created for user {user.email}: {session_id}")

    return {
        "session_id": str(session_id),
        "user_id": str(user.user_id),
        "email": user.email,
        "display_name": user.display_name,
        "expires_at": expires_at.isoformat(),
    }


async def validate_session(db: AsyncSession, session_id: str) -> Optional[Dict[str, Any]]:
    """
    Validate session by ID.
    Returns user info if valid, None if invalid/expired.
    """
    try:
        session_uuid = uuid.UUID(session_id)
    except (ValueError, AttributeError):
        logger.warning(f"Invalid session ID format: {session_id}")
        return None

    # Query session with user data
    result = await db.execute(
        select(SessionModel, User)
        .join(User, SessionModel.user_id == User.user_id)
        .where(SessionModel.session_id == session_uuid)
    )
    row = result.first()

    if not row:
        logger.warning(f"Session not found: {session_id}")
        return None

    session, user = row

    # Check if session is active
    if not session.is_active:
        logger.warning(f"Session inactive: {session_id}")
        return None

    # Check if session expired
    if session.expires_at < datetime.utcnow():
        logger.warning(f"Session expired: {session_id}")
        await invalidate_session(db, session_id)
        return None

    # Check if user is active
    if not user.is_active:
        logger.warning(f"User inactive: {user.email}")
        return None

    # Update last activity timestamp
    await db.execute(
        update(SessionModel)
        .where(SessionModel.session_id == session_uuid)
        .values(last_activity_at=datetime.utcnow())
    )
    await db.commit()

    return {
        "session_id": str(session.session_id),
        "user_id": str(user.user_id),
        "email": user.email,
        "display_name": user.display_name,
        "role": "user",  # Default role since column doesn't exist in database
    }


async def invalidate_session(db: AsyncSession, session_id: str) -> bool:
    """Invalidate a session by marking it inactive."""
    try:
        session_uuid = uuid.UUID(session_id)
    except (ValueError, AttributeError):
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