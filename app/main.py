# -----------------------------------------------------------------
# mian.py
# -----------------------------------------------------------------
# Staring point for med-z4 application
#
# Dependencies:
# pip install fastapi "uvicorn[standard]"
# pip install jinja2 python-multipart python-dotenv
#
# Run from root: uvicorn app.main:app --reload --port 8005
#    Access via: localhost:8005
#   Stop server: CTRL + C
# -----------------------------------------------------------------

# Main imports
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# Routes
from app.routes import auth, admin, health, dashboard, patient

# Import 'settings' object from root-level config file
from config import settings

print()
print(f"       Application Name: {settings.app.name}")
print(f"    Application Version: {settings.app.version}")
print(f"      Application Debug: {settings.app.debug}")
print(f"         Sample API URL: {settings.sample.api_url}")
print(f"Session Timeout Minutes: {settings.session.timeout_minutes}")
print(f"    Session Cookie Name: {settings.session.cookie_name}")
print(f" Session Cookie Max Age: {settings.session.cookie_max_age}")
print(f"          CCOW Base URL: {settings.ccow.base_url}")
print(f"   CCOW Health Endpoint: {settings.ccow.health_endpoint}")
print(f"         VistA Base URL: {settings.vista.base_url}")
print(f"  VistA Health Endpoint: {settings.vista.health_endpoint}")
print()

# Initialize the FastAPI app
app = FastAPI(title=settings.app.name, debug=settings.app.debug)

# Mount the static files directory
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Setup Jinja2 templates directory with auto-reload for development
templates = Jinja2Templates(directory="app/templates")
templates.env.auto_reload = True

# Register all routers
app.include_router(auth.router, tags=["auth"])
app.include_router(dashboard.router, tags=["dashboard"])
app.include_router(admin.router, tags=["admin"])
app.include_router(health.router, tags=["health"])
app.include_router(patient.router, tags=["patient"])


# Create root route handler
@app.get("/")
async def root():
    """Redirect to login page."""
    return RedirectResponse(url="/login")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.app.name}


# Simple route handler
@app.get("/hello", response_class=HTMLResponse)
async def hello_htmx():
    return"<p class='success-msg'>HTMX is working! Connection successful.</p>"
