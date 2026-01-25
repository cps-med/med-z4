# ---------------------------------------------------------------------
# api_client.py
# ---------------------------------------------------------------------
# Service Layers and External API Calls
# This script builds the initial "Administrative" logic. In a
# professional app, we don't put API calling logic inside our routes,
# we create a Service.
# ---------------------------------------------------------------------
# Step 1: Create the API Client (api_client.py), using httpx, a
# modern, async-friendly successor to requests.
# ---------------------------------------------------------------------

import httpx
from config import settings

async def fetch_external_user(user_id: int):
    """
    Fetches a specific user from the external API.
    Encapsulates the logic for calling med-z1 (later) or JSONPlaceholder (now).
    """
    url = f"{settings.sample.api_url}/users/{user_id}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=5.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            # Returning None or an empty dict allows the route to decide 
            # how to handle the error UI-wise.
            return None