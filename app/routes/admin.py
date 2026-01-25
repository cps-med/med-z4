# -----------------------------------------------------------------
# admin.py
# -----------------------------------------------------------------
# Router structure for "Admin" functions
# -----------------------------------------------------------------

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services import api_client

# We need to tell the router where the templates are
templates = Jinja2Templates(directory="app/templates")

# Create router instance
router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/test-fetch", response_class=HTMLResponse)
async def test_fetch(request: Request, user_id: int = 1):
    """
    FastAPI sees 'user_id' in the URL query string and converts it to integer
    """
    user_data = await api_client.fetch_external_user(user_id)

    if not user_data:
        return "<p style='color:red;'>User not found or API error.</p>"
    
    # Pass the 'user' dictionary directly into the template
    return templates.TemplateResponse(
        "partials/user_card.html",
        {"request": request, "user": user_data}
    )