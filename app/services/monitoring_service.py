# -----------------------------------------------------------
# app/services/monitoring_service.py
# -----------------------------------------------------------
# System monitoring and health check service functions
# -----------------------------------------------------------

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any, List, Optional
import httpx
import logging
from datetime import datetime, timezone

from config import settings

logger = logging.getLogger(__name__)


async def get_active_sessions(db: AsyncSession) -> Dict[str, Any]:
    """
    Fetch active sessions with user information.
    Returns summary and detailed session list.
    """
    try:
        query = text("""
            SELECT
                s.session_id,
                u.display_name,
                u.email,
                s.created_at,
                s.expires_at,
                s.last_activity_at,
                s.ip_address
            FROM auth.sessions s
            JOIN auth.users u ON s.user_id = u.user_id
            WHERE s.is_active = TRUE
            ORDER BY s.created_at DESC
        """)

        result = await db.execute(query)
        rows = result.fetchall()

        # Get summary counts
        summary_query = text("""
            SELECT
                COUNT(DISTINCT s.user_id) as unique_users,
                COUNT(s.session_id) as total_sessions
            FROM auth.sessions s
            WHERE s.is_active = TRUE
        """)

        summary_result = await db.execute(summary_query)
        summary_row = summary_result.fetchone()

        sessions = []
        for row in rows:
            # Calculate time ago for created_at
            if row[3]:  # created_at
                time_ago = _format_time_ago(row[3])
            else:
                time_ago = "Unknown"

            # Calculate expires in
            if row[4]:  # expires_at
                expires_in = _format_time_until(row[4])
            else:
                expires_in = "Unknown"

            sessions.append({
                "session_id": str(row[0])[:8] + "...",  # Truncated for display
                "display_name": row[1],
                "email": row[2],
                "created_ago": time_ago,
                "expires_in": expires_in,
                "ip_address": row[6] or "N/A"
            })

        return {
            "success": True,
            "summary": {
                "unique_users": summary_row[0] if summary_row else 0,
                "total_sessions": summary_row[1] if summary_row else 0
            },
            "sessions": sessions
        }

    except Exception as e:
        logger.error(f"Error fetching active sessions: {e}")
        return {
            "success": False,
            "error": str(e),
            "sessions": []
        }


async def get_database_health(db: AsyncSession) -> Dict[str, Any]:
    """
    Check database connectivity and return basic statistics.
    """
    try:
        # Test connection with simple query
        start_time = datetime.now()

        # Get patient count
        patient_count_query = text("""
            SELECT COUNT(*) FROM clinical.patient_demographics
        """)
        result = await db.execute(patient_count_query)
        patient_count = result.scalar()

        # Get last ETL update
        last_update_query = text("""
            SELECT MAX(last_updated) FROM clinical.patient_demographics
        """)
        result = await db.execute(last_update_query)
        last_update = result.scalar()

        end_time = datetime.now()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)

        # Format last update time
        if last_update:
            last_update_str = _format_time_ago(last_update)
        else:
            last_update_str = "Unknown"

        return {
            "success": True,
            "status": "Connected",
            "patient_count": patient_count,
            "last_etl_update": last_update_str,
            "response_time_ms": response_time_ms
        }

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "success": False,
            "status": "Error",
            "error": str(e)
        }


async def get_medz1_health() -> Dict[str, Any]:
    """
    Check if med-z1 application is reachable.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/", timeout=2.0)

            return {
                "success": True,
                "status": "Available",
                "status_code": response.status_code
            }

    except httpx.ConnectError:
        return {
            "success": False,
            "status": "Unreachable",
            "error": "Connection failed - is med-z1 running?"
        }
    except Exception as e:
        logger.error(f"med-z1 health check failed: {e}")
        return {
            "success": False,
            "status": "Error",
            "error": str(e)
        }


async def get_ccow_active_patients(session_id: str) -> Dict[str, Any]:
    """
    Fetch list of all active patient contexts from CCOW Vault.
    Requires authenticated session.
    """
    try:
        url = f"{settings.ccow.base_url}/ccow/active-patients"
        headers = {"X-Session-ID": session_id}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=2.0)

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"CCOW returned status {response.status_code}",
                    "contexts": []
                }

            data = response.json()

            # Transform contexts for display
            contexts = []
            for ctx in data.get("contexts", []):
                # Parse timestamp for sorting
                set_at_dt = None
                set_at_str = "Unknown"
                if ctx.get("set_at"):
                    set_at_dt = datetime.fromisoformat(ctx["set_at"].replace('Z', '+00:00'))
                    set_at_str = _format_time_ago(set_at_dt)

                contexts.append({
                    "email": ctx.get("email", "Unknown"),
                    "patient_id": ctx.get("patient_id", "N/A"),
                    "set_by": ctx.get("set_by", "unknown"),
                    "set_at": set_at_str,
                    "_set_at_dt": set_at_dt  # Keep for sorting
                })

            # Sort by timestamp descending (most recent first)
            contexts.sort(key=lambda x: x["_set_at_dt"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

            # Remove internal sorting field
            for ctx in contexts:
                ctx.pop("_set_at_dt", None)

            return {
                "success": True,
                "total_count": data.get("total_count", 0),
                "contexts": contexts
            }

    except Exception as e:
        logger.error(f"Error fetching CCOW active patients: {e}")
        return {
            "success": False,
            "error": str(e),
            "contexts": []
        }


async def get_ccow_history(session_id: str, limit: int = 30) -> Dict[str, Any]:
    """
    Fetch recent CCOW context change history (global scope).
    Requires authenticated session.

    Args:
        session_id: User's session UUID
        limit: Maximum number of events to return (default: 30)
    """
    try:
        url = f"{settings.ccow.base_url}/ccow/history"
        headers = {"X-Session-ID": session_id}
        params = {"scope": "global"}  # Note: CCOW Vault doesn't support limit parameter

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params, timeout=2.0)

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"CCOW returned status {response.status_code}",
                    "history": []
                }

            data = response.json()

            # Transform history events for display
            history = []
            for event in data.get("history", []):
                # Parse timestamp for sorting
                ts_dt = None
                timestamp_str = "Unknown"
                if event.get("timestamp"):
                    ts_dt = datetime.fromisoformat(event["timestamp"].replace('Z', '+00:00'))
                    timestamp_str = _format_time_ago(ts_dt)

                # Format action with emoji
                action = event.get("action", "unknown")
                action_display = "🔵 Set" if action == "set" else "⚪ Clear"

                history.append({
                    "action": action_display,
                    "email": event.get("email", "Unknown"),
                    "patient_id": event.get("patient_id") or "—",
                    "actor": event.get("actor", "unknown"),
                    "timestamp": timestamp_str,
                    "_timestamp_dt": ts_dt  # Keep for sorting
                })

            # Sort by timestamp descending (most recent first)
            history.sort(key=lambda x: x["_timestamp_dt"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

            # Get total count before limiting
            total_count = len(history)

            # Limit to requested number of events
            history = history[:limit]

            # Remove internal sorting field
            for event in history:
                event.pop("_timestamp_dt", None)

            return {
                "success": True,
                "total_count": total_count,
                "history": history
            }

    except Exception as e:
        logger.error(f"Error fetching CCOW history: {e}")
        return {
            "success": False,
            "error": str(e),
            "history": []
        }


# -----------------------------------------------------------
# Helper functions
# -----------------------------------------------------------

def _format_time_ago(dt: datetime) -> str:
    """Format datetime as '5 min ago', '2 hours ago', etc."""
    if dt.tzinfo is None:
        # Assume UTC if naive
        dt = dt.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    delta = now - dt

    seconds = delta.total_seconds()

    if seconds < 60:
        return f"{int(seconds)}s ago"
    elif seconds < 3600:
        return f"{int(seconds / 60)}m ago"
    elif seconds < 86400:
        return f"{int(seconds / 3600)}h ago"
    else:
        return f"{int(seconds / 86400)}d ago"


def _format_time_until(dt: datetime) -> str:
    """Format datetime as 'in 5 min', 'in 2 hours', 'expired', etc."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    delta = dt - now

    seconds = delta.total_seconds()

    if seconds < 0:
        return "expired"
    elif seconds < 60:
        return f"in {int(seconds)}s"
    elif seconds < 3600:
        return f"in {int(seconds / 60)}m"
    elif seconds < 86400:
        return f"in {int(seconds / 3600)}h"
    else:
        return f"in {int(seconds / 86400)}d"
