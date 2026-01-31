# med-z4

**Simple EHR Application with CCOW Integration**

med-z4 is a companion Electronic Health Record (EHR) application designed to work alongside med-z1 in the healthcare ecosystem. It serves as a CCOW (Clinical Context Object Workgroup) participant and context manager, enabling seamless patient context synchronization across multiple applications.

## Key Features

- **Shared Database Architecture**: Connects to the same PostgreSQL `medz1` database used by med-z1
- **CCOW Integration**: Bidirectional patient context synchronization with med-z1
- **Independent Sessions**: Uses separate session cookies (`med_z4_session_id`) to enable simultaneous logins to both applications
- **Database-Backed Authentication**: Full authentication with bcrypt password hashing and session management
- **Teal/Emerald Theme**: Visually distinct from med-z1's Blue/Slate theme
- **Port 8005**: Runs independently from med-z1 (port 8000)
- **HTMX Polling**: Real-time context updates with 5-second polling interval

## Prerequisites

**IMPORTANT**: Before setting up med-z4, you must have completed the full med-z1 setup, including:

- PostgreSQL container running with `medz1` database created and populated
- Authentication tables (`auth` schema) created and seeded with mock users
- Clinical data tables (`clinical` schema) created and populated via ETL pipelines
- CCOW Context Vault service (managed by med-z1)
- Python 3.10 or 3.11 installed on your development machine

If you have not completed the med-z1 setup, please refer to the [med-z1 Developer Setup Guide](docs/guide/med-z1-developer-setup-guide.md) before proceeding.

## Verify Required Infrastructure

Before setting up med-z4, verify that the required services from med-z1 are running:

### 1. Verify PostgreSQL is Running

```bash
# Check that PostgreSQL container is running
docker ps | grep postgres16

# Expected output should show a running container on port 5432
```

Test database connectivity:

```bash
# Connect to the medz1 database
docker exec -it postgres16 psql -U postgres -d medz1

# Verify connection
SELECT current_database();
-- Should return: medz1

# List schemas (should include: auth, clinical, reference, public)
\dn

# List tables in auth schema (should include: users, sessions, audit_logs)
\dt auth.*

# Exit psql
\q
```

### 2. Verify CCOW Vault is Available

The CCOW Vault service is managed by the med-z1 project and must be running for context synchronization.

```bash
# Test CCOW Vault health endpoint
curl http://localhost:8001/ccow/health

# Expected response: {"status":"healthy","service":"ccow-vault","version":"2.1"}
```

If the CCOW Vault is not running, start it from the med-z1 project:

```bash
# In a separate terminal, navigate to med-z1 project
cd ~/swdev/med/med-z1
source .venv/bin/activate

# Start CCOW Vault service
uvicorn ccow.main:app --port 8001 --reload
```

## Developer Setup

### 1. Clone med-z4 Repository

Create and navigate to the parent folder where you'd like to clone med-z4 (typically the same location as med-z1):

```bash
# Navigate to parent directory (same as med-z1)
cd ~/swdev/med

# Clone the repository
git clone https://github.com/cps-med/med-z4.git

# Navigate to project root
cd med-z4

# View project structure
ls -al
```

### 2. Add and Configure .env File

The med-z4 application uses a project-wide `.env` file for managing secrets and configuration. Ask a peer developer for a copy that you can place in the med-z4 root directory.

```bash
# Copy .env to project root (adjust source path as needed)
cp /path/to/.env ~/swdev/med/med-z4/
```

**Required Environment Variables:**

The `.env` file should contain the following key configuration settings:

```bash
# Application Settings
APP_NAME=med-z4
APP_VERSION=0.1.0
APP_PORT=8005
APP_DEBUG=True

# Session Management
SESSION_SECRET_KEY=your-secret-key-at-least-32-characters-long
SESSION_TIMEOUT_MINUTES=25
SESSION_COOKIE_NAME=med_z4_session_id

# PostgreSQL Database (same as med-z1)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=medz1
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-postgres-password

# CCOW Context Vault
CCOW_BASE_URL=http://localhost:8001
CCOW_HEALTH_ENDPOINT=/ccow/health

# VistA Real-time Service
VISTA_BASE_URL=http://localhost:8003
VISTA_HEALTH_ENDPOINT=/health
```

**Note**: The PostgreSQL password must match the password used when creating the PostgreSQL container during med-z1 setup.

### 3. Create Python Virtual Environment

med-z4 uses Python 3.10 or 3.11, the same versions supported by med-z1.

```bash
# Ensure you're in the med-z4 project root
cd ~/swdev/med/med-z4

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment (macOS/Linux)
source .venv/bin/activate

# For Windows users:
# .venv\Scripts\activate

# Verify virtual environment is active
# Your prompt should now show (.venv)
which python3
# Should show: /Users/your-username/swdev/med/med-z4/.venv/bin/python3
```

### 4. Install Dependencies

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Install all required dependencies from requirements.txt
pip install -r requirements.txt

# Verify installation by listing installed packages
pip list

# Expected packages include:
# fastapi, uvicorn, Jinja2, SQLAlchemy, asyncpg, bcrypt, httpx, etc.
```

### 5. Verify Configuration

Test that the application can load configuration settings correctly:

```bash
# Verify configuration loads without errors
python -c "from config import settings; print('Config OK')"

# Expected output: Config OK

# Optionally, view loaded configuration (without sensitive values)
python -c "from config import settings; print(f'App: {settings.app.name}'); print(f'Port: {settings.app.port}'); print(f'DB: {settings.postgres.db}')"

# Expected output:
# App: med-z4
# Port: 8005
# DB: medz1
```

### 6. Verify Database Connectivity (Optional)

Test that the application can connect to the PostgreSQL database:

```bash
# Quick database connectivity test
# Note: 'SELECT 1' is a standard SQL health check query that returns the literal value 1
# It's used to verify database connectivity without requiring any tables to exist
python -c "
import asyncio
from sqlalchemy import text
from database import engine

async def test_db():
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT 1'))
        print('✅ Database connected successfully!')

asyncio.run(test_db())
"
```

Expected output:
```
✅ Database connected successfully!
```

## Running the Application

With setup complete, you can now start the med-z4 application:

```bash
# Ensure you're in the project root with virtual environment activated
cd ~/swdev/med/med-z4
source .venv/bin/activate

# Start the FastAPI development server
uvicorn app.main:app --reload --port 8005

# The application will be available at:
# http://localhost:8005
```

**Multi-Service Development Workflow:**

For full CCOW context synchronization and the complete med-z1 ecosystem, run all four services in separate terminal windows:

```bash
# Terminal 1: med-z4 (this project)
cd ~/swdev/med/med-z4
source .venv/bin/activate
uvicorn app.main:app --port 8005 --reload

# Terminal 2: CCOW Vault (managed by med-z1)
cd ~/swdev/med/med-z1
source .venv/bin/activate
uvicorn ccow.main:app --port 8001 --reload

# Terminal 3: VistA RPC Broker (managed by med-z1)
cd ~/swdev/med/med-z1
source .venv/bin/activate
uvicorn vista.app.main:app --port 8003 --reload

# Terminal 4: med-z1 (companion application)
cd ~/swdev/med/med-z1
source .venv/bin/activate
uvicorn app.main:app --port 8000 --reload
```

**Note:** While med-z4 does not directly depend on the VistA RPC Broker service, running it ensures the full suite of med-z1 capabilities (including real-time VistA data retrieval) is available during development.

**Service URLs:**

- med-z4: http://localhost:8005
- med-z1: http://localhost:8000
- CCOW Vault: http://localhost:8001 (API docs at /docs)
- VistA RPC Broker: http://localhost:8003 (API docs at /docs)  

**Test Credentials:**

All mock users share the same password:

```text
Email: clinician.alpha@va.gov
Password: VaDemo2025!
```

Additional test accounts: `clinician.bravo@va.gov`, `clinician.charlie@va.gov`, etc.

## Deactivating the Virtual Environment

When you're done working on med-z4, you can deactivate the Python virtual environment:

```bash
deactivate
```

## Project Documentation

For comprehensive information about the med-z4 application architecture, features, and implementation guides:

- **Project Instructions**: [CLAUDE.md](CLAUDE.md) - Complete project overview and development patterns
- **Design Specification**: [docs/spec/med-z4-design.md](docs/spec/med-z4-design.md) - Technical design and implementation roadmap
- **Database Guide**: [docs/guide/med-z1-postgres-guide.md](docs/guide/med-z1-postgres-guide.md) - Shared database schema documentation
- **med-z1 Setup Guide**: [docs/guide/med-z1-developer-setup-guide.md](docs/guide/med-z1-developer-setup-guide.md) - Full med-z1 setup instructions
