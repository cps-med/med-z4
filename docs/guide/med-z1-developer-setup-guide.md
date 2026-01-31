# Med-Z1 Developer Setup Guide

This guide provides instructions for installing, configuring, and running the **med-z1** application on a development machine running the macOS or Linux operating system. For Linux machines, it is targeted for pop!_OS, but should be useful for other Linux variants.  

**Prerequistite:** This application is designed to run using Python version 3.11 on macOS machines and version 3.10 on Linux based machines. Higher versions of Python may have incompatibility issues witih some of the supporting dependencies, such as numpy, pandas, and polars.

## GIT Setup

Prior to getting started, ensure that you have a current version of git installed and configured on your local machine. One way to check for the existance of git is to run the command:  

```bash
which git
```

**macOS**  
For macOS environments, it is recommended that you use the standard Apple Xcode developer tools. Installation of the xCODE app is not required. Instead, you can install the **Command Line Tools** via the command below:

Install macOS Developer Tools
```bash
xcode-select --install
```

Verify
```bash
# check git version
git --version

# Check the path to the active developer directory
xcode-select -p
```

**Linux**
Most Linux distributions (including Pop!_OS) come with git pre-installed.  

If git is not installed, install via apt
```bash
sudo apt-get update
sudo apt-get install git
```

Verify
```bash
# Check git version
git --version
```

**GIT Configuration**
Set up basic information about yourself
```bash
git config --global user.name "Chuck Sylvester"
git config --global user.email chuck.sylvester@outlook.com
git config --global color.ui true
```

To display your Git settings:
```bash
git config --list
git config --local --list
git config --global --list
```

## Clone med-z1 Repo to Local Dev Machine

Create and CD to the folder where you would like to clone the med-z1 repo, e.g.  
```bash
mkdir -p ~/swdev/med
cd ~/swdev/med
```

Go to the GitHub med-z1 repo  
https://github.com/cps-med/med-z1  

Click the `Code` button and copy the HTTPS URL  
https://github.com/cps-med/med-z1.git  

Ensure that you are in the target folder where you would like to clone the repo, e.g.:
```bash
~/swdev/med
```

Run the git clone command from the terminal command line  
```bash
git clone https://github.com/cps-med/med-z1.git
```

CD to the med-z1 project folder  
```bash
cd med-z1
```

Take a look at the project structure from the terminal:  
```bash
# standard bash command
ls -al

# corutils installed + alias command (created in .zshrc)
ll

# tree utility (several variants)
tree -L 1
tree -L 1 -F
tree -d -L 2
```

## Add and Configure .env File

The med-z1 applications uses a project-wide .env file for managing secrets and other sensitive information. Ask a peer developer for a copy that you can place in the med-z1 root directory.  

Place .env in the project root folder, or copy/paste contents into .env file
```bash
cp .env ~/swdev/med/med-z1/
```

No additional configuration is required at this time. Once you have obtain the project-wide .env file and placed it in the project root directory, you should be good to go.  

## Verify Python v3.10 or v3.11 Availability

For Macbook users, macOS comes with a system version of Python pre-installed, but it is often outdated and not recommended for development. For Linux users, your machine will likely have version 3.10.x or 3.11.x preinstalled.  

You can check the version:
```bash
python3 --version
```

**macOS**
If your machine is running a version prior to or newer than 3.11, consider a new installation via Homebrew, the macOS package manager.  

Check if already installed:
```bash
brew --version
```

If not installed, install Homebrew:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the post-installation instructions to add Homebrew to your PATH.

Recommended Python Version: 3.11.x (avoid 3.12+ due to virtual environment quirks)

If you don't have Python 3.11.x, install it:
```bash
brew install python@3.11
```

After installation, you may need to add Python 3.11 to your PATH.

Homebrew will provide instructions, typically:
```bash
# Add to ~/.zshrc or ~/.bash_profile
echo 'export PATH="$(brew --prefix)/opt/python@3.11/libexec/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Verify Installation:
```bash
python3 --version  # Should show 3.11.x
pip3 --version     # Should show 24.x or 25.x
```

**Linux**
The recommended Python version is 3.10 or 3.11. If your development machine is not running either version, please takes steps to install. Specific instructions for Python installation on a Linux environment are not yet documented in this guide.  

## Create Python Virtual Environment

The med-z1 application uses a single, shared Python virtual environment. This environment is not under version control, so you will need to create the environmenet locally within your development project using the `requirements.txt` file. This will install all required dependencies into your local environment.  

Note that for performance and compatibility reasons, med-z1 expects Python version 3.11 on macOS and version 3.10 (or 3.11) on Linux.

Create virtual environment in project root directory (med-z1)  

This will create Python v3.10 (or v3.11) virtual environment for managing dependencies.
```bash
python3 -m venv .venv
```

Activate virtual environment:
```bash
# macOS/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

You can list the default "starter" dependencies in your new environment:  
```bash
pip list
```

Install dependencies
```bash
pip install -r requirements.txt
```

To ensure compatibility between macOS and Linux, several packages use the `>=` operator, as opposed to `==` for version numbers. This results in the proper versions being downloaded for the respective runtime environments.    

The specific items that use this notation are listed below:  

- numpy>=2.0.0
- pandas>=2.0.0
- polars>=1.0.0
- pydantic==2.12.5 (keep)
- pydantic_core==2.41.5 (remove)

To deactivate a Python virtual environment:
```bash
deactivate
```

## Install and Run Docker

The **med-z1** application uses three core services that run within Docker container images:  

- Microsoft SQL Server 2019
- PostgreSQL 16
- MinIO  

On macOS, these services are managed using Docker Desktop; however, there are significant performance gains on Linux by managing these services natively through the command line.  

### macOS Setup

**Docker Desktop** is the recommended container runtime for macOS development.

**Download and Install**:

1. Download from [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)
2. Choose "Apple Chip" or "Intel Chip" based on your Mac
3. Open the `.dmg` file and drag Docker to Applications folder
4. Launch Docker Desktop from Applications
5. Complete the setup wizard (I use recommended settings)
6. Login to Docker using a personal account
7. Add Docker to your dock for easy access

**Configure Docker Desktop** (optional):

1. Open Docker Desktop preferences
2. Go to Settings → General
3. Enable "Start Docker Desktop when you sign in" (optional)
4. Allocate resources (recommended: 4 CPUs, 8 GB RAM)

**Verify Installation**:

```bash
docker --version
# Expected output: Docker version 24.x.x or later
```

**Pull and Create Microsoft SQL Server Container**

It is best to use SQL Server 2019, not 2022. SQL Server 2022 has issues on Apple Silicon.

Pull Docker Image
```bash
# Pull image
docker pull mcr.microsoft.com/mssql/server:2019-latest
```

For Apple Silicon based machines:
```bash
# Create and run container
# Replace placeholder password value with correct value (from .env)

docker run --platform linux/amd64 \
  -e 'ACCEPT_EULA=Y' \
  -e 'SA_PASSWORD=YourSecurePassword123!' \
  -p 1433:1433 \
  --name sqlserver2019 \
  -d mcr.microsoft.com/mssql/server:2019-latest
```

For intel based machines (remove the --platform flag):
```bash
# Create and run container
# Replace placeholder password value with correct value (from .env)

docker run \
  -e 'ACCEPT_EULA=Y' \
  -e 'SA_PASSWORD=YourSecurePassword123!' \
  -p 1433:1433 \
  --name sqlserver2019 \
  -d mcr.microsoft.com/mssql/server:2019-latest
```

**Pull and Create PostgreSQL Container**

PostgreSQL is the **serving database** for med-z1, providing low-latency access to Gold-layer data.

```bash
# Create PostgreSQL container with password
# Replace placeholder password value with correct value (from .env)

docker run -d \
    --name postgres16 \
    -e POSTGRES_PASSWORD=yourpassword \
    -p 5432:5432 \
    -v postgres16-data:/var/lib/postgresql/data \
    postgres:16

# Verify container is running
docker ps | grep postgres16
```

**Pull and Create MinIO Container**

MinIO Setup:
```bash
# Create MinIO container with password
# Replace placeholder password value with correct value (from .env)

docker run -d --name med-insight-minio \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=admin \
  -e MINIO_ROOT_PASSWORD=password \
  -v $HOME/minio-data:/data \
  quay.io/minio/minio server /data --console-address ":9001"
```

**Verfify Docker Containers**  
Verify the newly installed containers by starting, stopping, and viewing them within the Docker Desktop app.  

### Linux Setup

The instructions below are for Docker **native engine** installation, using a **docker-compose.yaml** script.

Install Docker components
```bash
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

The Linux intallation uses a docker compose yaml file, which is under version control and located in the project root directory. this file, `docker-compose.yaml`, is used to define and start the required conatiner images.  

Run docker-compose.yaml script (from project root directory)
```bash
docker compose up -d
```

Other useful Docker CLI commands:
```bash

# List running processes
docker ps
or
docker ps -q

# Stop Everything
docker stop $(docker ps -q)

# Remove specific containers that are no longer needed
docker ps -a
docker rm <container_name_or_id>

# Remove ALL stopped containers
docker rm $(docker ps -aq)

# Remove Images (Free up Disk Space)
docker images
docker rmi <image_id_or_name>

# The "Nuclear" Option (full environment refresh)
# Delete all stopped containers, unused networks, and dangling images
docker system prune -a

# Verify that Docker Services are running
docker logs sqlserver2019
docker logs postgres16
docker logs med-insight-minio
```

## PostgreSQL Database Setup

Before running any ETL pipelines or setting up user authentication, you must create the `medz1` database. The instructions below are for creating the database only; steps for creating the required schemas and tables are provided later.  

**Creation:**  
```bash
# Connect to the default 'postgres' database
docker exec -it postgres16 psql -U postgres -d postgres

# List the current set of databases within the postgress server
# For firsttime setup, the list will not include medz1.
\l

# Create the medz1 database from psql prompt
CREATE DATABASE medz1;

# Verify creation
# Should now include medz1
\l

# Exit
\q
```

**Verification:**
```bash
# Connect to the newly created medz1 database
docker exec -it postgres16 psql -U postgres -d medz1

# Verify connection
SELECT current_database();
-- Should return: medz1

# Exit
\q
```

**Dropping an Existing Database:**  
If you need to completely remove an existing database, e.g., to begin a fresh installation, follow the instructions below:  

```bash
-- Connect to the default 'postgres' database
\c postgres

-- Drop the existing database (forcing active connections to close)
DROP DATABASE medz1 WITH (FORCE);
```

## PostgreSQL User Authentication Setup

This section guides you through setting up the user authentication schema and tables within the PostgreSQL `medz1` database and populating these tables with mock user data. This one-line command uses the PostgreSQL DDL script shown below.

Create Authentication Schema and Tables
```bash
docker exec -i postgres16 psql -U postgres -d medz1 < db/ddl/create_auth_tables.sql
```

Verify that schema and tables were created
```bash
# Start postgres with medz1 database
docker exec -it postgres16 psql -U postgres -d medz1

# Run the following from the psql promt
-- List all schemas
\dn

-- List all tables in the auth schema
\dt auth.*

-- View auth.users table structure
\d auth.users

-- View auth.sessions table structure
\d auth.sessions

-- View auth.audit_logs table structure
\d auth.audit_logs

-- Exit psql
\q
```

Load Mock User Data
```bash
docker exec -i postgres16 psql -U postgres -d medz1 < db/seeds/auth_users.sql
```

Verify Mock Users Were Loaded via SQL Query
```bash
docker exec -it postgres16 psql -U postgres -d medz1 -c "SELECT email, display_name, home_site_sta3n, is_active FROM auth.users ORDER BY email;"
```

You can now test the authentication system by logging into the med-z1 application.

Start the FastAPI application using Uvicorn
```bash
uvicorn app.main:app --reload
```

Start a browser and navigate to
```bash
http://127.0.0.1:8000/
```
You should be redirected to the login page where you can use these credentials

Test Credentials (all users share same password)
```text
Email: clinician.alpha@va.gov
Password: VaDemo2025!
```

## PostgreSQL AI Infrastructure Setup

This section explains the AI infrastructure tables within the PostgreSQL `medz1` database. These tables support the AI Clinical Insights feature, specifically enabling **conversation memory** using LangGraph's PostgreSQL checkpointer.

**Purpose:**
- Enable persistent chat history across page refreshes and login sessions
- Maintain user-scoped conversation memory (persists across logins)
- Isolate conversations by user ID + patient ICN
- Auto-clear history on patient changes (different ICN = new conversation)
- Manual clear via "Clear Chat History" button

**Note: Auto-Created Tables (No Manual Setup Required)**    

The LangGraph checkpoint tables are **automatically created** when the FastAPI application starts. The `AsyncPostgresSaver.setup()` method in the lifespan handler creates these tables in the `public` schema if they don't exist.

No manual DDL execution is required, simply start the application:

```bash
# Tables are auto-created during application startup
uvicorn app.main:app --reload
```

**What happens at startup:**
1. Application initializes LangGraph `AsyncPostgresSaver`
2. Calls `checkpointer.setup()` (idempotent - safe to run multiple times)
3. Creates 4 checkpoint tables in `public` schema if missing
4. Application logs confirm successful initialization

**Expected startup logs:**
```
============================================================
med-z1 application startup: Initializing components
============================================================
Initializing LangGraph AsyncPostgresSaver for conversation memory...
Checkpoint URL: postgresql://***@localhost:5432/medz1
✅ LangGraph checkpointer initialized successfully
   - Schema: public (LangGraph default)
   - Tables: checkpoints, checkpoint_writes, checkpoint_blobs, checkpoint_migrations
   - Conversation memory enabled
✅ AI Clinical Insights Agent initialized successfully
   - Tools: 4 tools available
   - Conversation memory: ENABLED
============================================================
```

### **Verify Tables Were Created**

After starting the application, verify the checkpoint tables:

```bash
# List checkpoint tables in public schema
docker exec -it postgres16 psql -U postgres -d medz1 -c "\dt public.*point*"
```

**Expected output:**
```
                List of relations
 Schema |         Name          | Type  |  Owner
--------+-----------------------+-------+----------
 public | checkpoint_blobs      | table | postgres
 public | checkpoint_migrations | table | postgres
 public | checkpoint_writes     | table | postgres
 public | checkpoints           | table | postgres
(4 rows)
```

### **Table Descriptions**

**LangGraph v3.x creates 4 tables:**

1. **`checkpoints`** - Main conversation state metadata (thread_id, checkpoint_id, parent_id)
2. **`checkpoint_writes`** - Transactional writes during checkpoint creation (internal LangGraph use)
3. **`checkpoint_blobs`** - Binary blob storage for large checkpoint data (performance optimization)
4. **`checkpoint_migrations`** - Schema version tracking for LangGraph upgrades

**View table structures:**
```bash
# View checkpoints table structure
docker exec -it postgres16 psql -U postgres -d medz1 -c "\d public.checkpoints"

# View checkpoint_blobs table structure
docker exec -it postgres16 psql -U postgres -d medz1 -c "\d public.checkpoint_blobs"
```

## MinIO Setup and Bucket Creation

The med-z1 application uses MinIO as an S3-compatible object storage system for the data lake. The primary file types that will be managed within MinIO are csv and Parquet. MinIO must be properly configured before running ETL pipelines, as the pipelines read and write parquet files to and from MinIO.  

The MinIO service should already be running from the `docker compose up -d` command executed earlier.  

Verify the container status
```bash
# Check that MinIO container is running
docker ps | grep minio

# View MinIO logs
docker logs med-insight-minio
```

Expected output should show the MinIO container is running on port 9000 (API) and port 9001 (console).

MinIO provides a web-based console for managing buckets and objects.

Open your web browser and navigate to:
```
http://localhost:9001
```

Login with credentials from your `.env` file:
```
Username: admin
Password: {admin password}
```

The ETL pipelines expect a bucket named `med-z1` (or name specified in `.env` file as `MINIO_BUCKET_NAME`).

Create the med-z1 bucket via web console
```text
2. Click "Create Bucket" button
3. Enter bucket name: med-z1
4. Click "Create Bucket"
5. Verify the bucket appears in the bucket list
```

**Test MinIO Connectivity**
Use the provided test script to verify Python can connect to MinIO and perform basic read/write operations:

```bash
# Ensure you're in the project root and virtual environment is activated
cd ~/swdev/med/med-z1
source .venv/bin/activate

# Run MinIO connectivity test (using -m flag to run as module)
python -m scripts.minio_test
```

## Install SQL Server Command-Line Tools

For a better developer experience, install Microsoft SQL Server command-line tools natively on your macOS or Linux machine. This allows you to run `sqlcmd` directly from your host terminal without using `docker exec`.

**macOS Setup**

```bash
# Add Microsoft repository
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
brew update

# Install SQL Server tools and ODBC drivers
brew install mssql-tools msodbcsql18

# Install unixODBC driver manager (required for Python pyodbc)
brew install unixodbc
```

**Add sqlcmd to PATH** (add to `~/.zshrc` or `~/.bash_profile`):

```bash
echo 'export PATH="/usr/local/opt/mssql-tools/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Verify Installation**:

```bash
# Test sqlcmd
sqlcmd '-?'

# Verify ODBC drivers
odbcinst -q -d
# Should see: [ODBC Driver 18 for SQL Server]
```

**Linux/Pop!_OS Setup**

```bash
# Import the public repository GPG keys
curl https://packages.microsoft.com/keys/microsoft.asc | sudo tee /etc/apt/trusted.gpg.d/microsoft.asc

# Register the Microsoft Ubuntu repository
# For Pop!_OS 22.04 (based on Ubuntu 22.04):
curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list

# Update package lists
sudo apt-get update

# Install mssql-tools18 (includes sqlcmd and bcp)
sudo ACCEPT_EULA=Y apt-get install -y mssql-tools18 unixodbc-dev
```

**Note:** The `ACCEPT_EULA=Y` environment variable accepts the Microsoft EULA automatically. You can also install interactively without this flag.

Add sqlcmd to PATH
```bash
# Add to your ~/.bashrc
echo 'export PATH="$PATH:/opt/mssql-tools18/bin"' >> ~/.bashrc

# Reload your shell configuration
source ~/.bashrc

# Verify installation
sqlcmd -?
```

Test Connection to SQL Server
```bash
# Test connection to your Docker SQL Server instance
# (update -P password with correct value from .env)
sqlcmd -S 127.0.0.1,1433 -U sa -P 'MyS3cur3P@ssw0rd' -C -Q "SELECT @@VERSION"
```

**Note:** The `-C` flag is required for sqlcmd 18+ to trust the server certificate.

## Create and Populate SQL Server Mock Data

The **med-z1** application uses Microsoft SQL Server 2019 to simulate the VA Corporate Data Warehouse (CDW) for local development. The mock CDW contains synthetic patient data for a number of VistA sites (aka "stations") and spans multiple clinical domains, such as Allergies, Vitals, Labs, Encounters, Clinical Notes, and Immunizations.

### CDWWork Database (VistA)

This section guides you through creating the **CDWWork** database schema and populating it with mock patient data.

Verify SQL Server Container is Running
```bash
# Check that SQL Server container is running
docker ps | grep sqlserver

# View SQL Server logs (should show "SQL Server is now ready for client connections")
docker logs sqlserver2019 | tail -20
```

**Create Database and Tables**
The project provides `_master.sql` scripts in the `create/` folder that orchestrate the creation of all tables in the correct dependency order.

Option 1: Using Shell Script with .env Password (Recommended)
```bash
# Navigate to the create scripts directory
cd ~/swdev/med/med-z1/mock/sql-server/cdwwork/create

# Run the shell script (sources password from .env)
./_master.sh
```

The `_master.sh` script loads the `CDWWORK_DB_PASSWORD` environment variable from your `.env` file and executes the `_master.sql` script.

Option 2: Direct sqlcmd Command
```bash
# Navigate to the create scripts directory
cd ~/swdev/med/med-z1/mock/sql-server/cdwwork/create

# Run sqlcmd directly with password
sqlcmd -S 127.0.0.1,1433 -U sa -P 'MyS3cur3P@ssw0rd' -C -i _master.sql
```

**Note:** Replace `'MyS3cur3P@ssw0rd'` with your actual SQL Server password from the `.env` file.

### Populate Mock Data

After creating the database structure, populate the tables with synthetic patient data.

Option 1: Using Shell Script with .env Password (Recommended)
```bash
# Navigate to the insert scripts directory
cd ~/swdev/med/med-z1/mock/sql-server/cdwwork/insert

# Run the shell script (sources password from .env)
./_master.sh
```

Option 2: Direct sqlcmd Command
```bash
# Navigate to the insert scripts directory
cd ~/swdev/med/med-z1/mock/sql-server/cdwwork/insert

# Run sqlcmd directly with password
sqlcmd -S 127.0.0.1,1433 -U sa -P 'MyS3cur3P@ssw0rd' -C -i _master.sql
```

**Note:** Replace `'MyS3cur3P@ssw0rd'` with your actual SQL Server password from the `.env` file.

Verify Database Creation via sqlcmd
```bash
# Connect to SQL Server interactively
sqlcmd -S 127.0.0.1,1433 -U sa -P 'MyS3cur3P@ssw0rd' -C
```

From the sqlcmd prompt, run verification queries:
```sql
-- List all databases (should see CDWWork)
SELECT name FROM sys.databases;
GO

-- Switch to CDWWork database
USE CDWWork;
GO

-- List all schemas
SELECT name FROM sys.schemas WHERE name IN ('Dim', 'SPatient', 'Vital', 'Allergy', 'RxOut', 'BCMA', 'Inpat', 'Chem');
GO

-- Count patients in SPatient.SPatient
SELECT COUNT(*) AS patient_count FROM SPatient.SPatient;
GO

-- Count vitals records
SELECT COUNT(*) AS vitals_count FROM Vital.VitalSign;
GO

-- Count medications records
SELECT COUNT(*) AS meds_count FROM RxOut.RxOutpat;
GO

-- Count lab results
SELECT COUNT(*) AS labs_count FROM Chem.LabChem;
GO

-- View sample patient data
SELECT TOP 5 PatientSID, PatientICN, PatientName, BirthDateTime, Gender, Sta3n
FROM SPatient.SPatient;
GO

-- Exit sqlcmd
EXIT
```

### CDWWork2 Database (Cerner / Oracle Health)

This section guides you through creating the **CDWWork2** database schema and populating it with mock patient data.  

**CDWWork2** simulates VA medical centers that have migrated to Oracle Health EHR system.

Follow the steps outlined above for CDWWork Option 1 or Option 2, but from the following locations:

 - med-z1/mock/sql-server/cdwwork2/create
 - med-z1/mock/sql-server/cdwwork2/insert

## Run ETL Data Pipelines

The **med-z1** ETL (Extract, Transform, Load) pipelines transform raw data from the SQL Server mock CDW into curated, query-optimized data for the PostgreSQL serving database. The pipelines follow the **medallion architecture** with three layers stored as Parquet files in MinIO, followed by loading into PostgreSQL.

Before running ETL pipelines, ensure the following are complete:

- PostgreSQL container running with `medz1` database created
- PostgreSQL auth schema and tables created (from previous section)
- MinIO container running with `med-z1` bucket created
- MinIO connectivity tested successfully (`python -m scripts.minio_test`)
- SQL Server container running with CDWWork and CDWWork2 databases populated
- Python virtual environment activated (`source .venv/bin/activate`)

**Create PostgreSQL Clinical Domain Tables**  
Before loading data, create the PostgreSQL table schemas for each clinical domain:
```bash
# Ensure you're in the project root with Python virtual environment activated
cd ~/swdev/med/med-z1
source .venv/bin/activate

# Create clinical tables by running each of the statements below
docker exec -i postgres16 psql -U postgres -d medz1 < db/ddl/patient_demographics.sql
docker exec -i postgres16 psql -U postgres -d medz1 < db/ddl/create_patient_vitals_table.sql
docker exec -i postgres16 psql -U postgres -d medz1 < db/ddl/create_patient_allergies_tables.sql
docker exec -i postgres16 psql -U postgres -d medz1 < db/ddl/create_patient_medications_tables.sql
docker exec -i postgres16 psql -U postgres -d medz1 < db/ddl/create_patient_flags_tables.sql
docker exec -i postgres16 psql -U postgres -d medz1 < db/ddl/create_patient_encounters_table.sql
docker exec -i postgres16 psql -U postgres -d medz1 < db/ddl/create_patient_labs_table.sql
docker exec -i postgres16 psql -U postgres -d medz1 < db/ddl/create_patient_clinical_notes_table.sql
docker exec -i postgres16 psql -U postgres -d medz1 < db/ddl/create_patient_immunizations_table.sql
docker exec -i postgres16 psql -U postgres -d medz1 < db/ddl/create_reference_vaccine_table.sql
```

Verify tables were created:
```bash
docker exec -it postgres16 psql -U postgres -d medz1 -c "\dt clinical.*"
```

Expected output should list **12 tables** in the `clinical` schema:

- patient_demographics, patient_vitals
- patient_allergies, patient_allergy_reactions
- patient_medications_outpatient, patient_medications_inpatient
- patient_flags, patient_flag_history
- patient_encounters, patient_labs, patient_clinical_notes, patient_immunizations

Additionally, verify the reference table was created:
```bash
docker exec -it postgres16 psql -U postgres -d medz1 -c "\dt reference.*"
```

Expected output should show **1 table** in the `reference` schema:
- vaccine (30 CVX-coded vaccines)

### Running ETL Pipelines by Domain

Each clinical domain has a complete pipeline (Bronze → Silver → Gold → Load). Run pipelines in the order shown below to respect data dependencies.  

**Important Note:** All of the clinical domain pipelines detailed below (1 through 10) can be run via a single shell script, as described later in this guide.

All ETL scripts are run as Python modules from the project root:

```bash
# Ensure you're in project root
cd ~/swdev/med/med-z1
source .venv/bin/activate
```

#### 1. Patient Demographics Pipeline

```bash
# Bronze: Extract raw patient data from SQL Server
python -m etl.bronze_patient
python -m etl.bronze_patient_address
python -m etl.bronze_patient_disability
python -m etl.bronze_patient_insurance
python -m etl.bronze_insurance_company

# Silver: Clean and harmonize
python -m etl.silver_patient

# Gold: Create query-optimized demographics
python -m etl.gold_patient

# Load: Insert into PostgreSQL
python -m etl.load_postgres_patient
```

#### 2. Vitals Pipeline

```bash
# Bronze: Extract vitals from SQL Server (CDWWork and CDWWork2)
python -m etl.bronze_vitals
python -m etl.bronze_cdwwork2_vitals

# Silver: Clean and harmonize
python -m etl.silver_vitals

# Gold: Create query-optimized vitals
python -m etl.gold_vitals

# Load: Insert into PostgreSQL
python -m etl.load_vitals
```

#### 3. Allergies Pipeline

```bash
# Bronze: Extract allergies and related dimension data
python -m etl.bronze_allergen
python -m etl.bronze_reaction
python -m etl.bronze_allergy_severity
python -m etl.bronze_patient_allergy
python -m etl.bronze_patient_allergy_reaction

# Silver: Clean and harmonize
python -m etl.silver_patient_allergies

# Gold: Create query-optimized allergies
python -m etl.gold_patient_allergies

# Load: Insert into PostgreSQL
python -m etl.load_patient_allergies
```

#### 4. Medications Pipeline

```bash
# Bronze: Extract medications from SQL Server
python -m etl.bronze_medications

# Silver: Clean and harmonize
python -m etl.silver_medications

# Gold: Create query-optimized medications
python -m etl.gold_patient_medications

# Load: Insert into PostgreSQL
python -m etl.load_medications
```

#### 5. Patient Flags Pipeline

```bash
# Bronze: Extract patient flags
python -m etl.bronze_patient_flags

# Silver: Clean and harmonize
python -m etl.silver_patient_flags

# Gold: Create query-optimized flags
python -m etl.gold_patient_flags

# Load: Insert into PostgreSQL
python -m etl.load_patient_flags
```

#### 6. Encounters (Inpatient) Pipeline

```bash
# Bronze: Extract inpatient encounters
python -m etl.bronze_inpatient

# Silver: Clean and harmonize
python -m etl.silver_inpatient

# Gold: Create query-optimized encounters
python -m etl.gold_inpatient

# Load: Insert into PostgreSQL
python -m etl.load_encounters
```

#### 7. Laboratory Results Pipeline

```bash
# Bronze: Extract lab results
python -m etl.bronze_labs

# Silver: Clean and harmonize
python -m etl.silver_labs

# Gold: Create query-optimized labs
python -m etl.gold_labs

# Load: Insert into PostgreSQL
python -m etl.load_labs
```

#### 8. Clinical Notes Pipeline
```bash
# Bronze: Extract Clinical Notes
python -m etl.bronze_clinical_notes_vista

# Silver: Clean and harmonize
python -m etl.silver_clinical_notes

# Gold: Create query-optimized clinical notes
python -m etl.gold_clinical_notes

# Load: Insert into PostgreSQL
python -m etl.load_clinical_notes
```

#### 9. Immunizations Pipeline
```bash
# Bronze: Extract Immunizations from CDWWork (VistA)
python -m etl.bronze_immunizations

# Bronze: Extract Immunizations from CDWWork2 (Cerner)
python -m etl.bronze_cdwwork2_immunizations

# Silver: Harmonize and deduplicate
python -m etl.silver_immunizations

# Gold: Create patient-centric immunization view
python -m etl.gold_immunizations

# Load: Insert into PostgreSQL
python -m etl.load_immunizations
```

#### 10. Drug-Drug Interaction (DDI) Reference Data Pipeline

The DDI pipeline provides reference data for the AI Clinical Insights feature. Unlike clinical domains, this pipeline does NOT load into PostgreSQL—the Gold Parquet is consumed directly by the AI service at runtime.

**Important Prerequisites:**
- MinIO `med-sandbox` bucket must exist
- Kaggle CSV file must be uploaded to: `med-sandbox/kaggle-data/ddi/db_drug_interactions.csv`

**Pipeline Steps:**
```bash
# Bronze: Extract from Kaggle CSV in MinIO
python -m etl.bronze_ddi

# Silver: Clean and normalize
python -m etl.silver_ddi

# Gold: Create AI-optimized reference
python -m etl.gold_ddi
```

### Verify ETL Pipeline Results
After running all pipelines, verify clinical domain data was successfully loaded into PostgreSQL.  

You can also verify that Parquet files were created in MinIO via the Web Console:
```bash
1. Navigate to http://localhost:9001
2. Login (admin / admin#123#2025)
3. Click "Buckets" → "med-z1"
4. Browse folders: `bronze/`, `silver/`, `gold/`
5. You should see Parquet files organized by domain
```

### Running All Pipelines with a Shell Script

For convenience, you can run all ETL pipelines (clinical domains + DDI reference data) sequentially via a single shell script.  

**Important Note:** The DDI pipeline requires the Kaggle CSV to exist in MinIO's `med-sandbox` bucket at path `kaggle-data/ddi/db_drug_interactions.csv`. If the file is missing, the script will fail at the DDI Bronze extraction step. See section **_10. Drug-Drug Interaction (DDI) Reference Data Pipeline_** above for DDI prerequisites and how to verify MinIO setup.  

Run the full ETL Pipeline:
```bash
./scripts/run_all_etl.sh
```

## Next Steps

With the ETL pipelines complete, you now have:

- Mock CDW data in SQL Server (simulates VA production CDW)
- Bronze/Silver/Gold Parquet files in MinIO (data lake)
- Query-optimized data in PostgreSQL (serving database for UI)

You can now start the FastAPI application and view patient data in the UI. Below are instructions for starting the three core FastAPI servers. You can start the services in any order, but it's best to start them in the order presented below.

From the project root directory, within separate terminal windows or tabs:
```bash
# Activate Python virtual environment
# Start the Vista RPC Broker Simulator (port 8003, separate terminal or tab)
uvicorn vista.app.main:app --reload --port 8003

# Activate Python virtual environment
# Start the CCOW Context Vault service (port 8001, separate terminal or tab)
uvicorn ccow.main:app --reload --port 8001

# Activate Python virtual environment
# Start the main med-z1 web application (port 8000, separate terminal or tab)
# Note that the port argument is optional, since it will default to 8000
uvicorn app.main:app --reload --port 8000

# Open browser to http://127.0.0.1:8000
# Optional URL: localhost:8000
# Login with: clinician.alpha@va.gov / VaDemo2025!
# Search for patient by ICN (e.g., ICN100001)
```
