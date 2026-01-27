# -----------------------------------------------------------
# app/services/ccow_service.py
# -----------------------------------------------------------
# CCOW Vault API integration service
# -----------------------------------------------------------

import httpx
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from config import settings

logger = logging.getLogger(__name__)


class CCOWService:
    """Service for CCOW Vault API interactions."""

    def __init__(self):
        self.base_url = settings.ccow.base_url
        self.timeout = 5.0  # 5 second timeout for CCOW calls

    async def join_context(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Join CCOW context as a participant.
        Returns context token and current patient ICN if available.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/ccow/join",
                    json={
                        "application_id": "med-z4",
                        "user_id": user_id,
                        "session_id": session_id,
                    }
                )
                response.raise_for_status()
                data = response.json()

                logger.info(f"Joined CCOW context: {data.get('context_token')}")
                return data

        except httpx.TimeoutException:
            logger.error("CCOW join timeout")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"CCOW join failed: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"CCOW join error: {e}")
            return None

    async def poll_context(self, context_token: str) -> Optional[Dict[str, Any]]:
        """
        Poll CCOW for current context.
        Returns current patient ICN and context status.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/ccow/context",
                    params={"context_token": context_token}
                )
                response.raise_for_status()
                data = response.json()

                logger.debug(f"CCOW context poll: {data.get('patient_icn')}")
                return data

        except httpx.TimeoutException:
            logger.warning("CCOW poll timeout")
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(f"CCOW poll failed: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"CCOW poll error: {e}")
            return None

    async def leave_context(self, context_token: str) -> bool:
        """
        Leave CCOW context (on logout).
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/ccow/leave",
                    json={"context_token": context_token}
                )
                response.raise_for_status()

                logger.info(f"Left CCOW context: {context_token}")
                return True

        except Exception as e:
            logger.error(f"CCOW leave error: {e}")
            return False

    async def set_context(self, context_token: str, patient_icn: str) -> bool:
        """
        Set patient context (optional - for future use if med-z4 becomes a manager).
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/ccow/context",
                    json={
                        "context_token": context_token,
                        "patient_icn": patient_icn
                    }
                )
                response.raise_for_status()

                logger.info(f"Set CCOW context: {patient_icn}")
                return True

        except Exception as e:
            logger.error(f"CCOW set context error: {e}")
            return False

    async def health_check(self) -> bool:
        """Check if CCOW Vault is available."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}{settings.ccow.health_endpoint}"
                )
                return response.status_code == 200
        except Exception:
            return False


# Singleton instance
ccow_service = CCOWService()