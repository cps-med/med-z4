# -----------------------------------------------------------------
# health.py
# -----------------------------------------------------------------
# Router structure for "Health Check" of CCOW and VistA services
# -----------------------------------------------------------------

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx

# Import 'settings' object from root-level config file
from config import settings

# Templates instance for this router
templates = Jinja2Templates(directory="app/templates")

# It is perfectly fine (and standard) to call this 'router'
router = APIRouter(prefix="/health", tags=["Monitoring"])

@router.get("/ccow", response_class=HTMLResponse)
async def check_ccow_health(request: Request):
    """
    Calls the external CCOW service health endpoint.
    """
    base_url = settings.ccow.base_url
    health_endpoint = settings.ccow.health_endpoint
    target_url = base_url + health_endpoint

    async with httpx.AsyncClient() as client:
        try:
            # Set a short timeout for health checks
            response = await client.get(target_url, timeout=2.0)
            data = response.json()
            status_code = response.status_code
        except Exception as e:
            data = {"status": "unreachable", "error": str(e)}
            status_code = 500

    # We can reuse our partial pattern or return a simple string for now
    color = "green" if status_code == 200 else "red"
    return f"""
    <div class="success-msg" style="border-color: {color};">
        <strong>CCOW Service Status:</strong> {data.get('status', 'Unknown')} (Code: {status_code})
    </div>
    """


@router.get("/vista", response_class=HTMLResponse)
async def check_vista_health(request: Request):
    """
    Calls the external VistA service health endpoint.
    """
    base_url = settings.vista.base_url
    health_endpoint = settings.vista.health_endpoint
    target_url = base_url + health_endpoint
    
    async with httpx.AsyncClient() as client:
        try:
            # We set a short timeout for health checks
            response = await client.get(target_url, timeout=2.0)
            data = response.json()
            status_code = response.status_code
        except Exception as e:
            data = {"status": "unreachable", "error": str(e)}
            status_code = 500

    # We can reuse our partial pattern or return a simple string for now
    color = "green" if status_code == 200 else "red"
    return f"""
    <div class="success-msg" style="border-color: {color};">
        <strong>VistA Service Status:</strong> {data.get('status', 'Unknown')} (Code: {status_code})
    </div>
    """