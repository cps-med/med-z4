# -----------------------------------------------------------
# app/services/ccow_service.py
# -----------------------------------------------------------
# CCOW Vault v2.1 API integration service
# -----------------------------------------------------------

import httpx
import logging
from typing import Optional, Dict, Any

from config import settings

logger = logging.getLogger(__name__)


class CCOWService:
    """
    Service for CCOW Vault v2.1 API interactions.

    Uses X-Session-ID header for authentication (cross-application pattern).
    CCOW Vault validates the session against the shared auth.sessions table
    and extracts user_id to provide per-user context isolation.
    """

    def __init__(self):
        self.base_url = settings.ccow.base_url
        self.timeout = 5.0  # 5 second timeout for CCOW calls

    async def get_active_patient(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current user's active patient context from CCOW Vault.

        Args:
            session_id: med-z4 session UUID (from med_z4_session_id cookie)

        Returns:
            Patient context dict with patient_id, set_by, set_at, etc.
            None if no active patient or on error.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/ccow/active-patient",
                    headers={"X-Session-ID": session_id}
                )

                if response.status_code == 404:
                    # No active patient for this user
                    return None

                response.raise_for_status()
                data = response.json()

                logger.debug(f"CCOW get_active_patient: {data.get('patient_id')}")
                return data

        except httpx.TimeoutException:
            logger.warning("CCOW get_active_patient timeout")
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(f"CCOW get_active_patient failed: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"CCOW get_active_patient error: {e}")
            return None

    async def set_active_patient(self, session_id: str, patient_icn: str) -> bool:
        """
        Set the current user's active patient context in CCOW Vault.

        Args:
            session_id: med-z4 session UUID
            patient_icn: Patient ICN to set as active

        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    f"{self.base_url}/ccow/active-patient",
                    headers={"X-Session-ID": session_id},
                    json={
                        "patient_id": patient_icn,
                        "set_by": "med-z4"
                    }
                )
                response.raise_for_status()

                logger.info(f"CCOW set_active_patient: {patient_icn}")
                return True

        except httpx.TimeoutException:
            logger.error("CCOW set_active_patient timeout")
            return False
        except httpx.HTTPStatusError as e:
            logger.error(f"CCOW set_active_patient failed: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"CCOW set_active_patient error: {e}")
            return False

    async def clear_active_patient(self, session_id: str) -> bool:
        """
        Clear the current user's active patient context in CCOW Vault.

        Args:
            session_id: med-z4 session UUID

        Returns:
            True if successful or no context to clear, False on error
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(
                    f"{self.base_url}/ccow/active-patient",
                    headers={"X-Session-ID": session_id}
                )

                if response.status_code in (204, 404):
                    # 204 = cleared, 404 = nothing to clear
                    logger.info("CCOW clear_active_patient: success")
                    return True

                response.raise_for_status()
                return True

        except Exception as e:
            logger.error(f"CCOW clear_active_patient error: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if CCOW Vault is available and get version info.

        Returns:
            Health check response dict or error dict
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}{settings.ccow.health_endpoint}"
                )
                if response.status_code == 200:
                    return response.json()
                return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}


# Singleton instance
ccow_service = CCOWService()