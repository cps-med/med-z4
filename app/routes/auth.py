# -----------------------------------------------------------
# app/routes/auth.py
# -----------------------------------------------------------

from fastapi import APIRouter, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from app.services.auth_service import authenticate_user, create_session, invalidate_session

from config import settings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Display login form."""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "settings": settings
    })


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user against database."""

    ip_address = request.client.host
    user_agent = request.headers.get("user-agent", "unknown")

    # Authenticate user with database
    user = await authenticate_user(db, email, password)

    if not user:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "settings": settings,
                "error": "Invalid email or password."
            },
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    # Create database session
    session_info = await create_session(db, user, ip_address, user_agent)

    # Redirect to dashboard with session cookie
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=settings.session.cookie_name,
        value=session_info["session_id"],
        max_age=settings.session.cookie_max_age,
        httponly=True,
        samesite="lax",
        secure=False,  # Set True in production with HTTPS
    )

    return response


@router.post("/logout")
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    """Invalidate session and redirect to login."""

    session_id = request.cookies.get(settings.session.cookie_name)

    if session_id:
        await invalidate_session(db, session_id)

    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key=settings.session.cookie_name)

    return response