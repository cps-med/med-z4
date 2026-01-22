# med-z1 PostgreSQL Serving Database Reference

**Document Version:** v1.1
**Last Updated:** 2026-01-22
**Database:** `medz1`
**PostgreSQL Version:** 16+

---

## Table of Contents

1. [Overview](#overview)
2. [Database Schema Organization](#database-schema-organization)
3. [Schema: `clinical`](#schema-clinical)
   - [patient_demographics](#table-clinicalpatient_demographics)
   - [patient_vitals](#table-clinicalpatient_vitals)
   - [patient_flags](#table-clinicalpatient_flags)
   - [patient_flag_history](#table-clinicalpatient_flag_history)
   - [patient_allergies](#table-clinicalpatient_allergies)
   - [patient_allergy_reactions](#table-clinicalpatient_allergy_reactions)
   - [patient_medications_outpatient](#table-clinicalpatient_medications_outpatient)
   - [patient_medications_inpatient](#table-clinicalpatient_medications_inpatient)
   - [patient_encounters](#table-clinicalpatient_encounters)
   - [patient_labs](#table-clinicalpatient_labs)
   - [patient_clinical_notes](#table-clinicalpatient_clinical_notes)
   - [patient_immunizations](#table-clinicalpatient_immunizations)
4. [Schema: `reference`](#schema-reference)
   - [vaccine](#table-referencevaccine)
5. [Schema: `auth`](#schema-auth)
   - [users](#table-authusers)
   - [sessions](#table-authsessions)
   - [audit_logs](#table-authaudit_logs)
6. [Schema: `public` (AI Checkpoint Tables)](#schema-public-ai-checkpoint-tables)
   - [checkpoints](#table-publiccheckpoints)
   - [checkpoint_writes](#table-publiccheckpoint_writes)
   - [checkpoint_blobs](#table-publiccheckpoint_blobs)
   - [checkpoint_migrations](#table-publiccheckpoint_migrations)
7. [Common Query Patterns](#common-query-patterns)
8. [Data Volume Estimates](#data-volume-estimates)

---

## Overview

The **med-z1 serving database**, `medz1`, is a PostgreSQL database that serves as the Gold layer serving database for the med-z1 application. It contains patient-centric clinical data optimized for low-latency UI queries.

**Key Characteristics:**
- **Data Source:** Transformed from Gold layer Parquet files (MinIO) via ETL pipelines
- **Patient Identity:** All clinical tables are keyed by `patient_key` (ICN - Integrated Care Number)
- **Schema Organization:** Tables organized by functional domain (`clinical`, `auth`, `reference`, `public`)
- **Index Strategy:** Patient-centric indexes optimized for dashboard and detail page queries
- **Data Freshness:** T-1 and earlier (historical data); complemented by VistA RPC Broker for T-0 (real-time)

---

## Database Schema Organization

The med-z1 database is organized into four functional schemas:

| Schema | Purpose | Tables |
|--------|---------|--------|
| `clinical` | Patient clinical data (demographics, vitals, medications, etc.) | 12 tables |
| `reference` | Reference data and lookup tables (CVX codes, etc.) | 1 table |
| `auth` | User authentication and session management | 3 tables |
| `public` | AI/ML infrastructure (LangGraph checkpoints for conversation memory) | 4 tables |

**Total Tables:** 20

**Note:** The AI checkpoint tables in the `public` schema are **auto-created** by LangGraph's `AsyncPostgresSaver.setup()` at application startup. No manual DDL execution is required.

---

## Schema: `clinical`

The `clinical` schema contains patient-centric clinical data tables. All tables are keyed by `patient_key` (ICN).

---

### Table: `clinical.patient_demographics`

**Purpose:** Patient demographic and administrative data optimized for UI queries.

**Primary Key:** `patient_key`

**Source:** Gold layer Parquet files (`demographics/*.parquet`)

#### Columns

| Column Name | Data Type | Nullable | Description | Example Values |
|-------------|-----------|----------|-------------|----------------|
| `patient_key` | VARCHAR(50) | NOT NULL | Internal unique identifier (currently same as ICN) | `"ICN100001"` |
| `icn` | VARCHAR(50) | NOT NULL | Integrated Care Number - primary VA patient identifier | `"ICN100001"` |
| `ssn` | VARCHAR(64) | NULL | Encrypted or hashed SSN (production) | `"123-45-6789"` |
| `ssn_last4` | VARCHAR(4) | NULL | Last 4 digits of SSN for display/verification | `"6789"` |
| `name_last` | VARCHAR(100) | NULL | Patient last name | `"DOOREE"` |
| `name_first` | VARCHAR(100) | NULL | Patient first name | `"ADAM"` |
| `name_display` | VARCHAR(200) | NULL | Formatted name for UI display (LAST, First) | `"DOOREE, ADAM"` |
| `dob` | DATE | NULL | Date of birth | `"1956-03-15"` |
| `age` | INTEGER | NULL | Current age calculated from DOB | `68` |
| `sex` | VARCHAR(1) | NULL | Biological sex | `"M"`, `"F"` |
| `gender` | VARCHAR(50) | NULL | Gender identity | `"Male"`, `"Female"`, `"Non-binary"` |
| `primary_station` | VARCHAR(10) | NULL | Primary VA station (Sta3n) | `"508"`, `"200"` |
| `primary_station_name` | VARCHAR(200) | NULL | Primary station name | `"Atlanta VA Medical Center"` |
| `address_street1` | VARCHAR(100) | NULL | Primary address street line 1 | `"123 Main St"` |
| `address_street2` | VARCHAR(100) | NULL | Primary address street line 2 | `"Apt 4B"` |
| `address_city` | VARCHAR(100) | NULL | Primary address city | `"Atlanta"` |
| `address_state` | VARCHAR(2) | NULL | Primary address state abbreviation | `"GA"`, `"CA"` |
| `address_zip` | VARCHAR(10) | NULL | Primary address ZIP code | `"30303"`, `"30303-1234"` |
| `phone_primary` | VARCHAR(20) | NULL | Primary phone number | `"404-555-1234"` |
| `insurance_company_name` | VARCHAR(100) | NULL | Primary insurance company name | `"Blue Cross Blue Shield"` |
| `marital_status` | VARCHAR(25) | NULL | Marital status | `"Married"`, `"Single"`, `"Divorced"`, `"Widowed"` |
| `religion` | VARCHAR(50) | NULL | Religion for spiritual care coordination | `"Catholic"`, `"Baptist"` |
| `service_connected_percent` | DECIMAL(5,2) | NULL | Service connected disability percentage (0-100) | `70.00`, `100.00` |
| `deceased_flag` | CHAR(1) | NULL | Deceased flag | `"Y"`, `"N"` |
| `death_date` | DATE | NULL | Date of death (if deceased) | `"2023-05-20"` |
| `veteran_status` | VARCHAR(50) | NULL | Veteran status | `"Veteran"` |
| `source_system` | VARCHAR(20) | NULL | Data source system | `"CDWWork"` |
| `last_updated` | TIMESTAMP | NULL | Record last updated timestamp | `"2025-12-10 14:23:45"` |

#### Indexes

| Index Name | Columns | Type | Notes |
|------------|---------|------|-------|
| `idx_patient_icn` | `icn` | B-tree | Fast ICN lookups |
| `idx_patient_name_last` | `name_last` | B-tree | Patient name searches |
| `idx_patient_name_first` | `name_first` | B-tree | Patient name searches |
| `idx_patient_ssn_last4` | `ssn_last4` | B-tree | Last 4 SSN verification |
| `idx_patient_station` | `primary_station` | B-tree | Station-based queries |
| `idx_patient_dob` | `dob` | B-tree | Age-based queries |

#### Constraints

- **Primary Key:** `patient_key`
- **Unique:** `icn`

---

### Table: `clinical.patient_vitals`

**Purpose:** Patient vital signs data with harmonized multi-source support (VistA + Cerner).

**Primary Key:** `vital_id` (auto-increment)

**Source:** Gold layer Parquet files (`vitals/*.parquet`)

#### Columns

| Column Name | Data Type | Nullable | Description | Example Values |
|-------------|-----------|----------|-------------|----------------|
| `vital_id` | SERIAL | NOT NULL | Auto-increment primary key | `1`, `2`, `3` |
| `patient_key` | VARCHAR(50) | NOT NULL | Patient ICN | `"ICN100001"` |
| `vital_sign_id` | BIGINT | NOT NULL | Source VitalSignSID (unique across sources) | `123456789` |
| `vital_type` | VARCHAR(100) | NOT NULL | Vital sign type | `"BLOOD PRESSURE"`, `"TEMPERATURE"`, `"WEIGHT"` |
| `vital_abbr` | VARCHAR(10) | NOT NULL | Vital abbreviation | `"BP"`, `"T"`, `"WT"`, `"HT"`, `"P"` |
| `taken_datetime` | TIMESTAMP | NOT NULL | When vital was taken | `"2025-12-10 08:30:00"` |
| `entered_datetime` | TIMESTAMP | NULL | When entered into VistA/Cerner | `"2025-12-10 08:35:00"` |
| `result_value` | VARCHAR(50) | NULL | Display value | `"120/80"`, `"98.6"`, `"180"` |
| `numeric_value` | DECIMAL(10,2) | NULL | Numeric value for single-value vitals | `98.6`, `180` |
| `systolic` | INTEGER | NULL | BP systolic (BP only) | `120` |
| `diastolic` | INTEGER | NULL | BP diastolic (BP only) | `80` |
| `metric_value` | DECIMAL(10,2) | NULL | Converted metric value (temp in C, weight in kg) | `37.0`, `81.6` |
| `unit_of_measure` | VARCHAR(20) | NULL | Unit of measure | `"mmHg"`, `"F"`, `"lb"`, `"in"`, `"/min"` |
| `qualifiers` | JSONB | NULL | JSON array of qualifiers (position, site, method) | `["Sitting", "Right Arm"]` |
| `location_id` | INTEGER | NULL | LocationSID from source system | `456` |
| `location_name` | VARCHAR(100) | NULL | Hospital/clinic location name | `"Primary Care Clinic"` |
| `location_type` | VARCHAR(50) | NULL | Location type | `"Outpatient"`, `"Inpatient"`, `"Emergency"` |
| `entered_by` | VARCHAR(100) | NULL | Staff name who entered vital | `"NURSE, JANE"` |
| `abnormal_flag` | VARCHAR(20) | NULL | Abnormality status | `"CRITICAL"`, `"HIGH"`, `"LOW"`, `"NORMAL"` |
| `bmi` | DECIMAL(5,2) | NULL | Calculated BMI (if WT and HT available) | `25.3` |
| `data_source` | VARCHAR(20) | NULL | Data origin | `"CDWWork"`, `"CDWWork2"`, `"CALCULATED"` |
| `last_updated` | TIMESTAMP | NULL | Record last updated timestamp | `"2025-12-10 08:35:00"` |

#### Indexes

| Index Name | Columns | Type | Notes |
|------------|---------|------|-------|
| `idx_patient_vitals_patient_date` | `patient_key`, `taken_datetime DESC` | B-tree | Primary query pattern |
| `idx_patient_vitals_type_date` | `vital_type`, `taken_datetime DESC` | B-tree | Vital type filtering |
| `idx_patient_vitals_recent` | `patient_key`, `vital_abbr`, `taken_datetime DESC` | B-tree | Recent vitals widget |
| `idx_patient_vitals_abnormal` | `abnormal_flag`, `taken_datetime DESC` | Partial | Abnormal vitals only (WHERE abnormal_flag IN ('CRITICAL', 'HIGH')) |
| `idx_patient_vitals_location_type` | `location_type` | B-tree | Location filtering |
| `idx_patient_vitals_data_source` | `data_source` | B-tree | Source system filtering |

#### Constraints

- **Primary Key:** `vital_id`
- **Unique:** `vital_sign_id`

---

### Table: `clinical.patient_flags`

**Purpose:** Patient record flags (safety alerts, behavioral flags) - denormalized for query performance.

**Primary Key:** `flag_id` (auto-increment)

**Source:** Gold layer Parquet files (`flags/*.parquet`)

#### Columns

| Column Name | Data Type | Nullable | Description | Example Values |
|-------------|-----------|----------|-------------|----------------|
| `flag_id` | SERIAL | NOT NULL | Auto-increment primary key | `1`, `2`, `3` |
| `patient_key` | VARCHAR(50) | NOT NULL | Patient ICN | `"ICN100001"` |
| `assignment_id` | BIGINT | NOT NULL | Unique assignment ID for upserts | `789456123` |
| `flag_name` | VARCHAR(100) | NOT NULL | Flag name | `"HIGH RISK FOR SUICIDE"`, `"MISSING PATIENT"` |
| `flag_category` | VARCHAR(2) | NOT NULL | Flag category | `"I"` (National Cat I), `"II"` (Local Cat II) |
| `flag_type` | VARCHAR(30) | NULL | Flag type | `"BEHAVIORAL"`, `"CLINICAL"`, `"RESEARCH"` |
| `is_active` | BOOLEAN | NOT NULL | Currently active flag | `true`, `false` |
| `assignment_status` | VARCHAR(20) | NOT NULL | Assignment status | `"ACTIVE"`, `"INACTIVE"` |
| `assignment_date` | TIMESTAMP | NOT NULL | Date flag was assigned | `"2024-01-15 09:00:00"` |
| `inactivation_date` | TIMESTAMP | NULL | Date flag was inactivated | `"2024-06-20 14:30:00"` |
| `owner_site` | VARCHAR(10) | NULL | Owning VA station (Sta3n) | `"508"` |
| `owner_site_name` | VARCHAR(100) | NULL | Owning station name | `"Atlanta VA Medical Center"` |
| `review_frequency_days` | INTEGER | NULL | Required review frequency in days | `90`, `180`, `365` |
| `next_review_date` | TIMESTAMP | NULL | Next required review date | `"2025-03-15 00:00:00"` |
| `review_status` | VARCHAR(20) | NULL | Review status | `"CURRENT"`, `"DUE SOON"`, `"OVERDUE"` |
| `last_action_date` | TIMESTAMP | NULL | Date of last flag action | `"2024-12-10 11:15:00"` |
| `last_action` | VARCHAR(50) | NULL | Last action taken | `"ASSIGNMENT"`, `"REVIEW"`, `"INACTIVATE"` |
| `last_action_by` | VARCHAR(100) | NULL | Staff who performed last action | `"DOCTOR, JANE"` |
| `last_updated` | TIMESTAMP | NULL | Record last updated timestamp | `"2025-12-10 14:23:45"` |

#### Indexes

| Index Name | Columns | Type | Notes |
|------------|---------|------|-------|
| `idx_patient_flags_patient` | `patient_key`, `is_active` | B-tree | Patient-centric queries |
| `idx_patient_flags_review` | `review_status`, `next_review_date` | B-tree | Review tracking |

#### Constraints

- **Primary Key:** `flag_id`
- **Unique:** `assignment_id`

---

### Table: `clinical.patient_flag_history`

**Purpose:** Audit trail for patient flag actions with sensitive narrative text.

**Primary Key:** `history_id` (auto-increment)

**Source:** Gold layer Parquet files (`flags/*.parquet`)

#### Columns

| Column Name | Data Type | Nullable | Description | Example Values |
|-------------|-----------|----------|-------------|----------------|
| `history_id` | SERIAL | NOT NULL | Auto-increment primary key | `1`, `2`, `3` |
| `assignment_id` | BIGINT | NOT NULL | Links to patient_flags.assignment_id | `789456123` |
| `patient_key` | VARCHAR(50) | NOT NULL | Patient ICN | `"ICN100001"` |
| `history_date` | TIMESTAMP | NOT NULL | Date of historical action | `"2024-01-15 09:00:00"` |
| `action_code` | SMALLINT | NOT NULL | Action code (1-5) | `1` (ASSIGNMENT), `2` (CONTINUE), `3` (INACTIVATE), `4` (EDIT), `5` (REVIEW) |
| `action_name` | VARCHAR(50) | NOT NULL | Action name | `"ASSIGNMENT"`, `"REVIEW"`, `"INACTIVATE"` |
| `entered_by_duz` | INTEGER | NOT NULL | Staff DUZ (VistA user ID) | `10958` |
| `entered_by_name` | VARCHAR(100) | NULL | Staff full name | `"DOCTOR, JANE"` |
| `approved_by_duz` | INTEGER | NOT NULL | Approver DUZ | `10958` |
| `approved_by_name` | VARCHAR(100) | NULL | Approver full name | `"DOCTOR, JANE"` |
| `tiu_document_ien` | INTEGER | NULL | TIU document IEN (VistA note reference) | `123456` |
| `history_comments` | TEXT | NULL | **SENSITIVE** - Narrative comments | `"Patient exhibits high-risk behavior..."` |
| `event_site` | VARCHAR(10) | NULL | Site where action occurred | `"508"` |
| `created_at` | TIMESTAMP | NULL | Record creation timestamp | `"2024-01-15 09:00:00"` |

#### Indexes

| Index Name | Columns | Type | Notes |
|------------|---------|------|-------|
| `idx_flag_history_assignment` | `assignment_id`, `history_date DESC` | B-tree | Assignment-based queries |
| `idx_flag_history_patient` | `patient_key`, `history_date DESC` | B-tree | Patient-based queries |

#### Constraints

- **Primary Key:** `history_id`

**⚠️ Security Note:** The `history_comments` column contains **sensitive clinical narrative text** and must be protected with appropriate access controls.

---

### Table: `clinical.patient_allergies`

**Purpose:** Patient allergy data (denormalized with comma-separated reactions for display).

**Primary Key:** `allergy_id` (auto-increment)

**Source:** Gold layer Parquet files (`allergies/*.parquet`)

#### Columns

| Column Name | Data Type | Nullable | Description | Example Values |
|-------------|-----------|----------|-------------|----------------|
| `allergy_id` | SERIAL | NOT NULL | Auto-increment primary key | `1`, `2`, `3` |
| `patient_key` | VARCHAR(50) | NOT NULL | Patient ICN | `"ICN100001"` |
| `allergy_sid` | BIGINT | NOT NULL | Source PatientAllergySID | `456789` |
| `allergen_local` | VARCHAR(255) | NOT NULL | Local allergen name as entered | `"PENICILLIN VK 500MG"`, `"SHELLFISH"` |
| `allergen_standardized` | VARCHAR(100) | NOT NULL | Standardized allergen name | `"PENICILLIN"`, `"SHELLFISH"` |
| `allergen_type` | VARCHAR(50) | NOT NULL | Allergen type | `"DRUG"`, `"FOOD"`, `"ENVIRONMENTAL"` |
| `severity` | VARCHAR(50) | NULL | Severity level | `"MILD"`, `"MODERATE"`, `"SEVERE"` |
| `severity_rank` | INTEGER | NULL | Severity rank for sorting (1=MILD, 2=MODERATE, 3=SEVERE) | `1`, `2`, `3` |
| `reactions` | TEXT | NULL | Comma-separated reaction names for display | `"Hives, Itching, Swelling"` |
| `reaction_count` | INTEGER | NULL | Count of documented reactions | `3`, `1` |
| `origination_date` | TIMESTAMP | NOT NULL | Date allergy was first documented | `"2020-05-10 10:30:00"` |
| `observed_date` | TIMESTAMP | NULL | Date allergy was observed | `"2020-05-10 10:30:00"` |
| `historical_or_observed` | VARCHAR(20) | NULL | Allergy type | `"HISTORICAL"`, `"OBSERVED"` |
| `originating_site` | VARCHAR(10) | NULL | VA station where allergy was documented | `"508"` |
| `originating_site_name` | VARCHAR(100) | NULL | Station name | `"Atlanta VA Medical Center"` |
| `originating_staff` | VARCHAR(100) | NULL | Staff who documented allergy | `"DOCTOR, JANE"` |
| `comment` | TEXT | NULL | **SENSITIVE** - Free-text clinical narrative | `"Patient reports anaphylaxis in 2019..."` |
| `is_active` | BOOLEAN | NULL | Currently active allergy | `true`, `false` |
| `verification_status` | VARCHAR(30) | NULL | Verification status | `"VERIFIED"`, `"UNVERIFIED"` |
| `is_drug_allergy` | BOOLEAN | NULL | TRUE if allergen_type = DRUG (for widget prioritization) | `true`, `false` |
| `last_updated` | TIMESTAMP | NULL | Record last updated timestamp | `"2025-12-12 09:15:00"` |

#### Indexes

| Index Name | Columns | Type | Notes |
|------------|---------|------|-------|
| `idx_patient_allergies_patient` | `patient_key`, `is_active` | B-tree | Patient-centric queries |
| `idx_patient_allergies_type` | `allergen_type`, `severity_rank DESC` | B-tree | Type filtering |
| `idx_patient_allergies_drug` | `patient_key`, `is_drug_allergy`, `severity_rank DESC` | Partial | Drug allergies only (WHERE is_active = TRUE) |
| `idx_patient_allergies_severity` | `severity_rank DESC`, `origination_date DESC` | Partial | Severity sorting (WHERE is_active = TRUE) |

#### Constraints

- **Primary Key:** `allergy_id`

---

### Table: `clinical.patient_allergy_reactions`

**Purpose:** Normalized detailed reaction data for each allergy (granular querying).

**Primary Key:** `reaction_id` (auto-increment)

**Source:** Gold layer Parquet files (`allergies/*.parquet`)

#### Columns

| Column Name | Data Type | Nullable | Description | Example Values |
|-------------|-----------|----------|-------------|----------------|
| `reaction_id` | SERIAL | NOT NULL | Auto-increment primary key | `1`, `2`, `3` |
| `allergy_sid` | BIGINT | NOT NULL | Links to source PatientAllergySID | `456789` |
| `patient_key` | VARCHAR(50) | NOT NULL | Patient ICN | `"ICN100001"` |
| `reaction_name` | VARCHAR(100) | NOT NULL | Reaction name | `"Hives"`, `"Itching"`, `"Swelling"`, `"Anaphylaxis"` |
| `created_at` | TIMESTAMP | NULL | Record creation timestamp | `"2025-12-12 09:15:00"` |

#### Indexes

| Index Name | Columns | Type | Notes |
|------------|---------|------|-------|
| `idx_allergy_reactions_allergy` | `allergy_sid` | B-tree | Links to patient_allergies |
| `idx_allergy_reactions_patient` | `patient_key` | B-tree | Patient-based queries |

#### Constraints

- **Primary Key:** `reaction_id`
- **Foreign Key:** `allergy_sid` → `clinical.patient_allergies.allergy_sid` (implicit)

---

### Table: `clinical.patient_medications_outpatient`

**Purpose:** Outpatient prescriptions (RxOut data) with refill tracking.

**Primary Key:** `medication_outpatient_id` (auto-increment)

**Source:** Gold layer Parquet files (`medications/*.parquet`)

#### Columns

| Column Name | Data Type | Nullable | Description | Example Values |
|-------------|-----------|----------|-------------|----------------|
| `medication_outpatient_id` | SERIAL | NOT NULL | Auto-increment primary key | `1`, `2`, `3` |
| `patient_icn` | VARCHAR(50) | NOT NULL | Patient ICN | `"ICN100001"` |
| `patient_key` | VARCHAR(50) | NOT NULL | Same as patient_icn | `"ICN100001"` |
| `rx_outpat_id` | BIGINT | NOT NULL | Source RxOutpatSID (duplicates exist in mock data) | `123456789` |
| `prescription_number` | VARCHAR(50) | NULL | Prescription number | `"RX-2024-001234"` |
| `local_drug_id` | BIGINT | NULL | LocalDrugSID | `10001` |
| `national_drug_id` | BIGINT | NULL | NationalDrugSID | `50001` |
| `drug_name_local` | VARCHAR(150) | NULL | Local drug name with dose | `"METFORMIN 500MG TAB"` |
| `drug_name_national` | VARCHAR(120) | NULL | National drug name | `"METFORMIN HCL 500MG TAB"` |
| `generic_name` | VARCHAR(120) | NULL | Generic name | `"METFORMIN HYDROCHLORIDE"` |
| `trade_name` | VARCHAR(120) | NULL | Trade/brand name | `"GLUCOPHAGE"` |
| `drug_strength` | VARCHAR(50) | NULL | Drug strength | `"500MG"`, `"10MG"` |
| `drug_unit` | VARCHAR(50) | NULL | Drug unit | `"TAB"`, `"CAP"`, `"ML"` |
| `dosage_form` | VARCHAR(50) | NULL | Dosage form | `"TABLET"`, `"CAPSULE"`, `"SOLUTION"` |
| `drug_class` | VARCHAR(100) | NULL | Drug class | `"ANTIDIABETIC"`, `"ANTIHYPERTENSIVE"` |
| `drug_class_code` | VARCHAR(20) | NULL | Drug class code | `"HS502"`, `"CV150"` |
| `dea_schedule` | VARCHAR(10) | NULL | DEA schedule | `"C-II"`, `"C-IV"`, `null` |
| `ndc_code` | VARCHAR(20) | NULL | National Drug Code | `"00378-0112-01"` |
| `issue_date` | TIMESTAMP | NULL | Date prescription was issued | `"2024-11-15 10:30:00"` |
| `rx_status` | VARCHAR(30) | NULL | Original prescription status | `"ACTIVE"`, `"EXPIRED"`, `"DISCONTINUED"` |
| `rx_status_computed` | VARCHAR(30) | NULL | Computed status with business logic | `"ACTIVE"`, `"EXPIRED"`, `"DISCONTINUED"` |
| `rx_type` | VARCHAR(30) | NULL | Prescription type | `"PRESCRIPTION"`, `"REFILL"` |
| `quantity_ordered` | DECIMAL(12,4) | NULL | Quantity ordered | `90.0000`, `30.0000` |
| `days_supply` | INTEGER | NULL | Days supply | `90`, `30` |
| `refills_allowed` | INTEGER | NULL | Total refills allowed | `5`, `3` |
| `refills_remaining` | INTEGER | NULL | Refills remaining | `3`, `0` |
| `unit_dose` | VARCHAR(50) | NULL | Unit dose | `"1 TAB"` |
| `latest_fill_number` | INTEGER | NULL | Latest fill number | `2`, `5` |
| `latest_fill_date` | TIMESTAMP | NULL | Latest fill date | `"2025-01-15 14:00:00"` |
| `latest_fill_status` | VARCHAR(30) | NULL | Latest fill status | `"FILLED"`, `"PARTIALLY FILLED"` |
| `latest_quantity_dispensed` | DECIMAL(12,4) | NULL | Latest quantity dispensed | `90.0000` |
| `latest_days_supply` | INTEGER | NULL | Latest days supply dispensed | `90` |
| `sig` | TEXT | NULL | Complete signature/directions | `"TAKE ONE TABLET BY MOUTH TWICE DAILY WITH MEALS"` |
| `sig_route` | VARCHAR(50) | NULL | Route | `"ORAL"`, `"TOPICAL"`, `"INTRAVENOUS"` |
| `sig_schedule` | VARCHAR(50) | NULL | Schedule | `"BID"`, `"TID"`, `"QID"`, `"PRN"` |
| `expiration_date` | TIMESTAMP | NULL | Prescription expiration date | `"2025-11-15 00:00:00"` |
| `discontinued_date` | TIMESTAMP | NULL | Date prescription was discontinued | `"2025-03-20 09:00:00"` |
| `discontinue_reason` | VARCHAR(100) | NULL | Reason for discontinuation | `"NO LONGER CLINICALLY INDICATED"` |
| `is_controlled_substance` | BOOLEAN | NULL | DEA controlled substance (Schedule II-V) | `true`, `false` |
| `is_active` | BOOLEAN | NULL | Currently active (not discontinued, not expired) | `true`, `false` |
| `days_until_expiration` | INTEGER | NULL | Days until expiration (negative if expired) | `120`, `-30` |
| `provider_name` | VARCHAR(100) | NULL | Prescribing provider name | `"DOCTOR, JANE"` |
| `ordering_provider_name` | VARCHAR(100) | NULL | Ordering provider name | `"DOCTOR, JANE"` |
| `pharmacy_name` | VARCHAR(100) | NULL | Pharmacy name | `"Atlanta VA Pharmacy"` |
| `clinic_name` | VARCHAR(100) | NULL | Clinic name | `"Primary Care Clinic"` |
| `facility_name` | VARCHAR(100) | NULL | Facility name | `"Atlanta VA Medical Center"` |
| `sta3n` | VARCHAR(10) | NULL | VA station number | `"508"` |
| `cmop_indicator` | CHAR(1) | NULL | CMOP (mail-order) indicator | `"Y"`, `"N"` |
| `mail_indicator` | CHAR(1) | NULL | Mail delivery indicator | `"Y"`, `"N"` |
| `source_system` | VARCHAR(50) | NULL | Data source system | `"CDWWork"` |
| `last_updated` | TIMESTAMP | NULL | Record last updated timestamp | `"2025-12-13 10:00:00"` |

#### Indexes

| Index Name | Columns | Type | Notes |
|------------|---------|------|-------|
| `idx_patient_medications_out_patient_date` | `patient_icn`, `issue_date DESC` | B-tree | Patient-centric queries |
| `idx_patient_medications_out_active` | `patient_icn`, `is_active`, `issue_date DESC` | Partial | Active meds only (WHERE is_active = TRUE) |
| `idx_patient_medications_out_controlled` | `patient_icn`, `is_controlled_substance`, `issue_date DESC` | Partial | Controlled substances (WHERE is_controlled_substance = TRUE) |
| `idx_patient_medications_out_drug_class` | `drug_class`, `issue_date DESC` | B-tree | Drug class filtering |
| `idx_patient_medications_out_rx_status` | `rx_status_computed`, `issue_date DESC` | B-tree | Status filtering |

#### Constraints

- **Primary Key:** `medication_outpatient_id`

---

### Table: `clinical.patient_medications_inpatient`

**Purpose:** Inpatient medication administration (BCMA data) with variance tracking.

**Primary Key:** `medication_inpatient_id` (auto-increment)

**Source:** Gold layer Parquet files (`medications/*.parquet`)

#### Columns

| Column Name | Data Type | Nullable | Description | Example Values |
|-------------|-----------|----------|-------------|----------------|
| `medication_inpatient_id` | SERIAL | NOT NULL | Auto-increment primary key | `1`, `2`, `3` |
| `patient_icn` | VARCHAR(50) | NOT NULL | Patient ICN | `"ICN100001"` |
| `patient_key` | VARCHAR(50) | NOT NULL | Same as patient_icn | `"ICN100001"` |
| `bcma_log_id` | BIGINT | NOT NULL | Source BCMAMedicationLogSID | `987654321` |
| `inpatient_sid` | BIGINT | NULL | Inpatient stay SID | `555123` |
| `order_number` | VARCHAR(50) | NULL | Order number | `"ORD-2024-999"` |
| `local_drug_id` | BIGINT | NULL | LocalDrugSID | `10001` |
| `national_drug_id` | BIGINT | NULL | NationalDrugSID | `50001` |
| `drug_name_local` | VARCHAR(150) | NULL | Local drug name with dose | `"INSULIN REGULAR HUMAN 100 UNITS/ML"` |
| `drug_name_national` | VARCHAR(120) | NULL | National drug name | `"INSULIN REGULAR 100 UNITS/ML"` |
| `generic_name` | VARCHAR(120) | NULL | Generic name | `"INSULIN REGULAR"` |
| `trade_name` | VARCHAR(120) | NULL | Trade name | `"HUMULIN R"` |
| `drug_strength` | VARCHAR(50) | NULL | Drug strength | `"100 UNITS/ML"` |
| `drug_unit` | VARCHAR(50) | NULL | Drug unit | `"ML"`, `"UNITS"` |
| `dosage_form` | VARCHAR(50) | NULL | Dosage form | `"SOLUTION"`, `"INJECTION"` |
| `drug_class` | VARCHAR(100) | NULL | Drug class | `"ANTIDIABETIC"` |
| `drug_class_code` | VARCHAR(20) | NULL | Drug class code | `"HS502"` |
| `dea_schedule` | VARCHAR(10) | NULL | DEA schedule | `"C-II"`, `null` |
| `ndc_code` | VARCHAR(20) | NULL | National Drug Code | `"00002-8215-01"` |
| `action_type` | VARCHAR(30) | NULL | Administration action | `"GIVEN"`, `"HELD"`, `"REFUSED"`, `"MISSING DOSE"` |
| `action_status` | VARCHAR(30) | NULL | Action status | `"COMPLETED"`, `"INCOMPLETE"` |
| `action_datetime` | TIMESTAMP | NULL | When action occurred | `"2025-01-10 08:00:00"` |
| `scheduled_datetime` | TIMESTAMP | NULL | When scheduled | `"2025-01-10 08:00:00"` |
| `ordered_datetime` | TIMESTAMP | NULL | When ordered | `"2025-01-09 18:00:00"` |
| `dosage_ordered` | VARCHAR(100) | NULL | Dosage ordered | `"10 UNITS"` |
| `dosage_given` | VARCHAR(100) | NULL | Dosage given | `"10 UNITS"` |
| `route` | VARCHAR(50) | NULL | Administration route | `"PO"`, `"IV"`, `"IM"`, `"SC"` |
| `unit_of_administration` | VARCHAR(50) | NULL | Unit | `"UNITS"`, `"MG"` |
| `schedule_type` | VARCHAR(30) | NULL | Schedule type | `"SCHEDULED"`, `"PRN"` |
| `schedule` | VARCHAR(50) | NULL | Schedule | `"BID"`, `"QID"`, `"Q6H"` |
| `administration_variance` | BOOLEAN | NULL | Variance occurred during administration | `true`, `false` |
| `variance_type` | VARCHAR(50) | NULL | Type of variance | `"LATE ADMINISTRATION"`, `"WRONG DOSE"` |
| `variance_reason` | VARCHAR(100) | NULL | Reason for variance | `"PATIENT REFUSED"`, `"OUT OF STOCK"` |
| `is_iv_medication` | BOOLEAN | NULL | IV (intravenous) medication | `true`, `false` |
| `iv_type` | VARCHAR(30) | NULL | IV type | `"CONTINUOUS"`, `"INTERMITTENT"` |
| `infusion_rate` | VARCHAR(50) | NULL | Infusion rate | `"100 ML/HR"` |
| `is_controlled_substance` | BOOLEAN | NULL | DEA controlled substance | `true`, `false` |
| `administered_by` | VARCHAR(100) | NULL | Staff who administered | `"NURSE, JANE"` |
| `ordering_provider` | VARCHAR(100) | NULL | Ordering provider | `"DOCTOR, JANE"` |
| `ward_name` | VARCHAR(100) | NULL | Ward name | `"Medical ICU"` |
| `facility_name` | VARCHAR(100) | NULL | Facility name | `"Atlanta VA Medical Center"` |
| `sta3n` | VARCHAR(10) | NULL | VA station number | `"508"` |
| `source_system` | VARCHAR(50) | NULL | Data source system | `"CDWWork"` |
| `last_updated` | TIMESTAMP | NULL | Record last updated timestamp | `"2025-12-13 10:30:00"` |

#### Indexes

| Index Name | Columns | Type | Notes |
|------------|---------|------|-------|
| `idx_patient_medications_inp_patient_date` | `patient_icn`, `action_datetime DESC` | B-tree | Patient-centric queries |
| `idx_patient_medications_inp_action_type` | `action_type`, `action_datetime DESC` | B-tree | Action type filtering |
| `idx_patient_medications_inp_controlled` | `patient_icn`, `is_controlled_substance`, `action_datetime DESC` | Partial | Controlled substances (WHERE is_controlled_substance = TRUE) |
| `idx_patient_medications_inp_variance` | `patient_icn`, `administration_variance`, `action_datetime DESC` | Partial | Variance tracking (WHERE administration_variance = TRUE) |
| `idx_patient_medications_inp_iv` | `patient_icn`, `is_iv_medication`, `action_datetime DESC` | Partial | IV meds (WHERE is_iv_medication = TRUE) |
| `idx_patient_medications_inp_drug_class` | `drug_class`, `action_datetime DESC` | B-tree | Drug class filtering |

#### Constraints

- **Primary Key:** `medication_inpatient_id`

---

### Table: `clinical.patient_encounters`

**Purpose:** Patient inpatient encounters (admissions) with length-of-stay tracking.

**Primary Key:** `encounter_id` (auto-increment)

**Source:** Gold layer Parquet files (`encounters/*.parquet`)

#### Columns

| Column Name | Data Type | Nullable | Description | Example Values |
|-------------|-----------|----------|-------------|----------------|
| `encounter_id` | SERIAL | NOT NULL | Auto-increment primary key | `1`, `2`, `3` |
| `patient_key` | VARCHAR(50) | NOT NULL | Patient ICN | `"ICN100001"` |
| `inpatient_id` | BIGINT | NOT NULL | Source InpatientSID | `789123456` |
| `admit_datetime` | TIMESTAMP | NOT NULL | Admission date/time | `"2024-12-01 14:30:00"` |
| `admit_location_id` | INTEGER | NULL | Ward/Location SID at admission | `123` |
| `admit_location_name` | VARCHAR(100) | NULL | Ward name at admission | `"Emergency Department"` |
| `admit_location_type` | VARCHAR(50) | NULL | Location type at admission | `"Emergency"`, `"Inpatient"` |
| `admit_diagnosis_code` | VARCHAR(20) | NULL | ICD-10 admission diagnosis code | `"I21.9"`, `"J44.1"` |
| `admitting_provider_id` | INTEGER | NULL | Provider SID | `456` |
| `admitting_provider_name` | VARCHAR(200) | NULL | Provider full name | `"DOCTOR, JANE"` |
| `discharge_datetime` | TIMESTAMP | NULL | Discharge date/time (NULL if active) | `"2024-12-05 10:00:00"`, `null` |
| `discharge_date_id` | INTEGER | NULL | Discharge date dimension SID | `20241205` |
| `discharge_location_id` | INTEGER | NULL | Ward/Location SID at discharge | `456` |
| `discharge_location_name` | VARCHAR(100) | NULL | Ward name at discharge | `"Medical Ward 3B"` |
| `discharge_location_type` | VARCHAR(50) | NULL | Location type at discharge | `"Inpatient"` |
| `discharge_diagnosis_code` | VARCHAR(20) | NULL | ICD-10 discharge diagnosis code | `"I21.9"` |
| `discharge_diagnosis_text` | VARCHAR(100) | NULL | Discharge diagnosis description | `"Acute myocardial infarction"` |
| `discharge_disposition` | VARCHAR(50) | NULL | Discharge disposition | `"Home"`, `"SNF"`, `"Rehab"`, `"AMA"`, `"Deceased"` |
| `length_of_stay` | INTEGER | NULL | LOS in days (from CDW) | `4`, `7`, `15` |
| `total_days` | INTEGER | NULL | Days from admit to discharge (or now if active) | `4`, `20` |
| `encounter_status` | VARCHAR(20) | NULL | Encounter status | `"Active"`, `"Discharged"` |
| `is_active` | BOOLEAN | NOT NULL | True if currently admitted (no discharge date) | `true`, `false` |
| `admission_category` | VARCHAR(30) | NULL | Admission category | `"Active Admission"`, `"Short Stay"`, `"Extended Stay"` |
| `is_recent` | BOOLEAN | NOT NULL | Admitted or discharged within last 30 days | `true`, `false` |
| `is_extended_stay` | BOOLEAN | NOT NULL | Active admission with total_days > 14 | `true`, `false` |
| `sta3n` | VARCHAR(10) | NULL | VA station number | `"508"` |
| `facility_name` | VARCHAR(100) | NULL | Facility name | `"Atlanta VA Medical Center"` |
| `source_system` | VARCHAR(50) | NULL | Data source system | `"CDWWork"` |
| `last_updated` | TIMESTAMP | NULL | Record last updated timestamp | `"2025-12-15 09:00:00"` |

#### Indexes

| Index Name | Columns | Type | Notes |
|------------|---------|------|-------|
| `idx_patient_encounters_patient_date` | `patient_key`, `admit_datetime DESC` | B-tree | Patient-centric queries |
| `idx_patient_encounters_admit_date` | `admit_datetime DESC` | B-tree | Admission date sorting |
| `idx_patient_encounters_discharge_date` | `discharge_datetime DESC` | Partial | Discharge date sorting (WHERE discharge_datetime IS NOT NULL) |
| `idx_patient_encounters_active` | `patient_key`, `admit_datetime DESC` | Partial | Active admissions (WHERE is_active = TRUE) |
| `idx_patient_encounters_recent` | `patient_key`, `admit_datetime DESC` | Partial | Recent encounters (WHERE is_recent = TRUE) |
| `idx_patient_encounters_facility` | `sta3n`, `admit_datetime DESC` | B-tree | Facility queries |
| `idx_patient_encounters_admit_location_type` | `admit_location_type` | B-tree | Location type filtering |
| `idx_patient_encounters_discharge_location_type` | `discharge_location_type` | B-tree | Location type filtering |

#### Constraints

- **Primary Key:** `encounter_id`
- **Unique:** `inpatient_id`

---

### Table: `clinical.patient_labs`

**Purpose:** Patient laboratory results with abnormal value tracking.

**Primary Key:** `lab_id` (auto-increment)

**Source:** Gold layer Parquet files (`labs/*.parquet`)

#### Columns

| Column Name | Data Type | Nullable | Description | Example Values |
|-------------|-----------|----------|-------------|----------------|
| `lab_id` | SERIAL | NOT NULL | Auto-increment primary key | `1`, `2`, `3` |
| `patient_key` | VARCHAR(50) | NOT NULL | Patient ICN | `"ICN100001"` |
| `lab_chem_sid` | BIGINT | NOT NULL | Source LabChemSID | `123456789` |
| `lab_test_sid` | INTEGER | NOT NULL | Test definition ID | `1001` |
| `lab_test_name` | VARCHAR(200) | NOT NULL | Lab test name | `"Sodium"`, `"Glucose"`, `"Hemoglobin A1c"` |
| `lab_test_code` | VARCHAR(50) | NULL | Lab test code | `"NA"`, `"GLU"`, `"HBA1C"` |
| `loinc_code` | VARCHAR(20) | NULL | LOINC code | `"2951-2"`, `"2339-0"` |
| `panel_name` | VARCHAR(200) | NULL | Panel/battery name | `"Basic Metabolic Panel"`, `"Lipid Panel"` |
| `accession_number` | VARCHAR(50) | NOT NULL | Accession number | `"CH 20251211-001"` |
| `result_value` | VARCHAR(100) | NULL | Display result value | `"142"`, `"Positive"`, `"6.5"` |
| `result_numeric` | DECIMAL(18,6) | NULL | Numeric result for trending | `142.000000`, `6.500000` |
| `result_unit` | VARCHAR(50) | NULL | Result unit | `"mmol/L"`, `"mg/dL"`, `"%"` |
| `abnormal_flag` | VARCHAR(10) | NULL | Abnormal flag | `"H"`, `"L"`, `"H*"`, `"L*"`, `"PANIC"` |
| `is_abnormal` | BOOLEAN | NULL | Quick abnormal check | `true`, `false` |
| `is_critical` | BOOLEAN | NULL | Critical/panic values requiring immediate attention | `true`, `false` |
| `ref_range_text` | VARCHAR(100) | NULL | Reference range text | `"135 - 145"`, `"Negative"`, `"<5.7"` |
| `ref_range_low` | DECIMAL(18,6) | NULL | Parsed reference range low value | `135.000000` |
| `ref_range_high` | DECIMAL(18,6) | NULL | Parsed reference range high value | `145.000000` |
| `collection_datetime` | TIMESTAMP | NOT NULL | When specimen was collected | `"2025-12-11 08:00:00"` |
| `result_datetime` | TIMESTAMP | NOT NULL | When result became available | `"2025-12-11 10:30:00"` |
| `location_id` | INTEGER | NULL | LocationSID | `789` |
| `collection_location` | VARCHAR(100) | NULL | Lab location name | `"Laboratory"`, `"Primary Care Clinic"` |
| `collection_location_type` | VARCHAR(50) | NULL | Location type | `"Laboratory"`, `"Outpatient"` |
| `specimen_type` | VARCHAR(50) | NULL | Specimen type | `"Serum"`, `"Whole Blood"`, `"Plasma"` |
| `sta3n` | VARCHAR(10) | NULL | VA station number | `"508"` |
| `performing_lab_sid` | INTEGER | NULL | Lab that performed test | `100` |
| `ordering_provider_sid` | INTEGER | NULL | Provider who ordered test | `456` |
| `vista_package` | VARCHAR(10) | NULL | VistA package | `"CH"` (Chemistry), `"LR"` (Lab) |
| `last_updated` | TIMESTAMP | NULL | Record last updated timestamp | `"2025-12-16 11:00:00"` |

#### Indexes

| Index Name | Columns | Type | Notes |
|------------|---------|------|-------|
| `idx_patient_labs_patient_date` | `patient_key`, `collection_datetime DESC` | B-tree | Patient-centric queries |
| `idx_patient_labs_test_date` | `lab_test_name`, `collection_datetime DESC` | B-tree | Test name filtering |
| `idx_patient_labs_panel` | `panel_name`, `collection_datetime DESC` | Partial | Panel filtering (WHERE panel_name IS NOT NULL) |
| `idx_patient_labs_abnormal` | `is_abnormal`, `is_critical`, `collection_datetime DESC` | Partial | Abnormal/critical results (WHERE is_abnormal = TRUE) |
| `idx_patient_labs_recent` | `patient_key`, `panel_name`, `collection_datetime DESC` | B-tree | Recent labs widget |
| `idx_patient_labs_location_type` | `collection_location_type` | B-tree | Location filtering |
| `idx_patient_labs_accession` | `accession_number`, `lab_test_sid` | B-tree | Panel grouping |

#### Constraints

- **Primary Key:** `lab_id`
- **Unique:** `lab_chem_sid`

---

### Table: `clinical.patient_clinical_notes`

**Purpose:** Patient clinical notes (TIU documents) with SOAP-formatted narrative text.

**Primary Key:** `note_id` (auto-increment)

**Source:** Gold layer Parquet files (`clinical_notes/*.parquet`)

#### Columns

| Column Name | Data Type | Nullable | Description | Example Values |
|-------------|-----------|----------|-------------|----------------|
| `note_id` | SERIAL | NOT NULL | Auto-increment primary key | `1`, `2`, `3` |
| `patient_key` | VARCHAR(50) | NOT NULL | Patient ICN | `"ICN100001"` |
| `tiu_document_sid` | BIGINT | NOT NULL | Source TIUDocumentSID | `987654321` |
| `document_definition_sid` | INTEGER | NOT NULL | Note type definition ID | `3` |
| `document_title` | VARCHAR(200) | NOT NULL | Document title | `"GEN MED PROGRESS NOTE"`, `"CARDIOLOGY CONSULT"` |
| `document_class` | VARCHAR(50) | NOT NULL | Document class | `"Progress Notes"`, `"Consults"`, `"Discharge Summaries"`, `"Imaging"` |
| `vha_standard_title` | VARCHAR(200) | NULL | VHA enterprise standard title | `"GENERAL MEDICINE PROGRESS NOTE"` |
| `status` | VARCHAR(50) | NOT NULL | Document status | `"COMPLETED"`, `"UNSIGNED"`, `"AMENDED"` |
| `reference_datetime` | TIMESTAMP | NOT NULL | Clinical date of note (primary sort key) | `"2025-11-20 10:00:00"` |
| `entry_datetime` | TIMESTAMP | NOT NULL | Date note was authored/entered | `"2025-11-20 10:30:00"` |
| `days_since_note` | INTEGER | NULL | Days since note was written | `63`, `120` |
| `note_age_category` | VARCHAR(20) | NULL | Note age category | `"<30 days"`, `"30-90 days"`, `"90-180 days"`, `">180 days"` |
| `author_sid` | BIGINT | NULL | Author StaffSID | `10958` |
| `author_name` | VARCHAR(200) | NULL | Author full name | `"DOCTOR, JANE"` |
| `cosigner_sid` | BIGINT | NULL | Cosigner StaffSID (if applicable) | `10959` |
| `cosigner_name` | VARCHAR(200) | NULL | Cosigner full name | `"ATTENDING, JOHN"` |
| `visit_sid` | BIGINT | NULL | Associated VisitSID | `555123` |
| `sta3n` | VARCHAR(10) | NULL | VA station number | `"508"` |
| `facility_name` | VARCHAR(200) | NULL | Facility name | `"Atlanta VA Medical Center"` |
| `document_text` | TEXT | NULL | **SENSITIVE** - Full narrative text of clinical note (SOAP format) | `"SUBJECTIVE: Patient reports..."` |
| `text_length` | INTEGER | NULL | Note text character count | `1250`, `3500` |
| `text_preview` | VARCHAR(500) | NULL | First 200 characters of note text for list views | `"SUBJECTIVE: Patient reports chest pain..."` |
| `tiu_document_ien` | VARCHAR(50) | NULL | TIU IEN (VistA identifier) | `"12345"` |
| `source_system` | VARCHAR(50) | NULL | Data source system | `"CDWWork"`, `"CDWWork2"` |
| `last_updated` | TIMESTAMP | NULL | Record last updated timestamp | `"2026-01-02 14:00:00"` |

#### Indexes

| Index Name | Columns | Type | Notes |
|------------|---------|------|-------|
| `idx_clinical_notes_patient_date` | `patient_key`, `reference_datetime DESC` | B-tree | Primary query pattern |
| `idx_clinical_notes_class_date` | `document_class`, `reference_datetime DESC` | B-tree | Document class filtering |
| `idx_clinical_notes_age_category` | `note_age_category`, `reference_datetime DESC` | Partial | Age category filtering (WHERE note_age_category IS NOT NULL) |
| `idx_clinical_notes_author` | `author_sid`, `reference_datetime DESC` | Partial | Author queries (WHERE author_sid IS NOT NULL) |
| `idx_clinical_notes_facility` | `sta3n`, `reference_datetime DESC` | B-tree | Facility queries |
| `idx_clinical_notes_recent` | `patient_key`, `document_class`, `reference_datetime DESC` | B-tree | Recent notes widget |

#### Constraints

- **Primary Key:** `note_id`
- **Unique:** `tiu_document_sid`

**⚠️ Security Note:** The `document_text` column contains **sensitive clinical narrative text** (full SOAP notes) and must be protected with appropriate access controls.

---

### Table: `clinical.patient_immunizations`

**Purpose:** Patient immunization records with CVX-coded vaccines for AI compliance checking.

**Primary Key:** `immunization_id` (auto-increment)

**Source:** Gold layer Parquet files (`immunizations/*.parquet`)

#### Columns

| Column Name | Data Type | Nullable | Description | Example Values |
|-------------|-----------|----------|-------------|----------------|
| `immunization_id` | SERIAL | NOT NULL | Auto-increment primary key | `1`, `2`, `3` |
| `patient_key` | VARCHAR(50) | NOT NULL | Patient ICN | `"ICN100001"` |
| `immunization_sid` | BIGINT | NOT NULL | Source system ID (PatientImmunizationSID or VaccineAdminSID) | `123456789` |
| `cvx_code` | VARCHAR(10) | NULL | CDC CVX code | `"208"` (COVID-19 Pfizer), `"141"` (Flu), `"115"` (Tdap) |
| `vaccine_name` | VARCHAR(255) | NULL | Standardized vaccine name (UPPERCASE) | `"COVID-19, MRNA, LNP-S, PF, 30 MCG/0.3 ML DOSE"` |
| `vaccine_name_local` | VARCHAR(255) | NULL | Original vaccine name as entered by clinician | `"COVID-19 Pfizer BioNTech Adult"` |
| `administered_datetime` | TIMESTAMP | NOT NULL | When vaccine was administered | `"2024-09-15 10:00:00"` |
| `series` | VARCHAR(50) | NULL | Display format for series tracking | `"1 of 2"`, `"BOOSTER"`, `"ANNUAL 2024"` |
| `dose_number` | INTEGER | NULL | Parsed dose number | `1`, `2`, `3` |
| `total_doses` | INTEGER | NULL | Parsed total doses in series | `2`, `3` |
| `is_series_complete` | BOOLEAN | NULL | TRUE if patient has received all doses in series | `true`, `false` |
| `dose` | VARCHAR(50) | NULL | Dose amount | `"0.5 ML"`, `"0.3 ML"` |
| `route` | VARCHAR(50) | NULL | Administration route | `"IM"`, `"SC"`, `"PO"`, `"Intranasal"` |
| `site_of_administration` | VARCHAR(100) | NULL | Anatomical site | `"Left Deltoid"`, `"Right Thigh"`, `"Right Deltoid"` |
| `adverse_reaction` | VARCHAR(255) | NULL | Adverse reaction description | `"Soreness at injection site"`, `"Fever, chills"` |
| `has_adverse_reaction` | BOOLEAN | NULL | TRUE if adverse reaction documented | `true`, `false` |
| `provider_name` | VARCHAR(100) | NULL | Administering provider name | `"NURSE, JANE"` |
| `location_sid` | INTEGER | NULL | LocationSID from source system | `456` |
| `location_name` | VARCHAR(100) | NULL | Hospital/clinic location name | `"Immunization Clinic"` |
| `location_type` | VARCHAR(50) | NULL | Location type | `"Outpatient"`, `"Inpatient"` |
| `station_name` | VARCHAR(100) | NULL | VA facility name | `"Atlanta VA Medical Center"` |
| `sta3n` | SMALLINT | NULL | VA station number | `508`, `200`, `630` |
| `comments` | TEXT | NULL | Free-text clinical notes | `"Patient tolerated vaccine well"` |
| `is_annual_vaccine` | BOOLEAN | NULL | TRUE for annual influenza vaccines | `true`, `false` |
| `is_covid_vaccine` | BOOLEAN | NULL | TRUE for COVID-19 vaccines | `true`, `false` |
| `source_system` | VARCHAR(20) | NULL | Data source system | `"CDWWork"` (VistA), `"CDWWork2"` (Cerner) |
| `last_updated` | TIMESTAMP | NULL | Record last updated timestamp | `"2026-01-14 10:00:00"` |

#### Indexes

| Index Name | Columns | Type | Notes |
|------------|---------|------|-------|
| `idx_immunizations_patient_date` | `patient_key`, `administered_datetime DESC` | B-tree | Primary query pattern (most common) |
| `idx_immunizations_cvx` | `cvx_code`, `administered_datetime DESC` | B-tree | CVX code queries for AI/compliance |
| `idx_immunizations_series` | `patient_key`, `cvx_code`, `dose_number`, `administered_datetime DESC` | B-tree | Series tracking |
| `idx_immunizations_incomplete` | `patient_key`, `is_series_complete`, `administered_datetime DESC` | Partial | Incomplete series (WHERE is_series_complete = FALSE) |
| `idx_immunizations_reactions` | `patient_key`, `has_adverse_reaction`, `administered_datetime DESC` | Partial | Adverse reactions (WHERE has_adverse_reaction = TRUE) |
| `idx_immunizations_annual` | `patient_key`, `administered_datetime DESC` | Partial | Annual vaccines (WHERE is_annual_vaccine = TRUE) |
| `idx_immunizations_covid` | `patient_key`, `administered_datetime DESC` | Partial | COVID-19 vaccines (WHERE is_covid_vaccine = TRUE) |
| `idx_immunizations_location_type` | `location_type` | B-tree | Location filtering |
| `idx_immunizations_data_source` | `source_system` | B-tree | Source system filtering |

#### Constraints

- **Primary Key:** `immunization_id`
- **Unique:** `immunization_sid`

---

## Schema: `reference`

The `reference` schema contains reference data and lookup tables.

---

### Table: `reference.vaccine`

**Purpose:** CDC CVX code reference table for vaccine standardization and AI compliance checking.

**Primary Key:** `cvx_code`

**Source:** CDC CVX standard codes (https://www2.cdc.gov/vaccines/iis/iisstandards/vaccines.asp)

#### Columns

| Column Name | Data Type | Nullable | Description | Example Values |
|-------------|-----------|----------|-------------|----------------|
| `cvx_code` | VARCHAR(10) | NOT NULL | CDC CVX code (primary identifier) | `"208"`, `"141"`, `"115"` |
| `vaccine_name` | VARCHAR(255) | NOT NULL | Full vaccine name (official CDC name) | `"COVID-19, mRNA, LNP-S, PF, 30 mcg/0.3 mL dose"` |
| `vaccine_short_name` | VARCHAR(100) | NULL | Abbreviated name for UI display | `"COVID-19 Pfizer"`, `"FLU-INJ"`, `"TDAP"` |
| `vaccine_group` | VARCHAR(100) | NULL | Vaccine family grouping for UI filters | `"COVID-19"`, `"Influenza"`, `"Hepatitis"`, `"Tdap/DTaP"` |
| `typical_series_pattern` | VARCHAR(50) | NULL | Expected series pattern | `"2-dose"`, `"3-dose"`, `"Annual"`, `"Booster"`, `"Single-dose"` |
| `is_active` | BOOLEAN | NULL | FALSE if vaccine no longer in use or superseded | `true`, `false` |
| `notes` | TEXT | NULL | Additional information (age recommendations, contraindications, CDC guidance) | `"Ages 50+, doses 2-6 months apart"` |
| `last_updated` | TIMESTAMP | NULL | Record last updated timestamp | `"2026-01-14 09:00:00"` |

#### Indexes

| Index Name | Columns | Type | Notes |
|------------|---------|------|-------|
| `idx_reference_vaccine_group` | `vaccine_group`, `vaccine_name` | Partial | Vaccine group filtering (WHERE is_active = TRUE) |
| `idx_reference_vaccine_active` | `is_active`, `vaccine_name` | B-tree | Active vaccines only |

#### Constraints

- **Primary Key:** `cvx_code`

**Seed Data:** Contains 30 common vaccines (childhood, adult, annual influenza, COVID-19).

---

## Schema: `auth`

The `auth` schema contains user authentication and session management tables.

---

### Table: `auth.users`

**Purpose:** User credentials and profile information for med-z1 application.

**Primary Key:** `user_id` (UUID)

**Source:** Application-managed (user registration/admin provisioning)

#### Columns

| Column Name | Data Type | Nullable | Description | Example Values |
|-------------|-----------|----------|-------------|----------------|
| `user_id` | UUID | NOT NULL | Auto-generated user ID | `"550e8400-e29b-41d4-a716-446655440000"` |
| `email` | VARCHAR(255) | NOT NULL | User email address (username for login) | `"jane.doctor@va.gov"` |
| `password_hash` | VARCHAR(255) | NOT NULL | Bcrypt hash of user password (never store plaintext) | `"$2b$12$..."` |
| `display_name` | VARCHAR(255) | NOT NULL | Display name | `"Dr. Jane Doctor"` |
| `first_name` | VARCHAR(100) | NULL | First name | `"Jane"` |
| `last_name` | VARCHAR(100) | NULL | Last name | `"Doctor"` |
| `home_site_sta3n` | INTEGER | NULL | Primary VA site assignment (Sta3n code) | `508`, `200` |
| `is_active` | BOOLEAN | NULL | Account is active | `true`, `false` |
| `is_locked` | BOOLEAN | NULL | Account is locked (security) | `true`, `false` |
| `failed_login_attempts` | INTEGER | NULL | Failed login attempt count | `0`, `3` |
| `last_login_at` | TIMESTAMP | NULL | Last successful login timestamp | `"2026-01-22 08:30:00"` |
| `created_at` | TIMESTAMP | NULL | Account creation timestamp | `"2025-11-01 10:00:00"` |
| `updated_at` | TIMESTAMP | NULL | Account last updated timestamp | `"2026-01-22 08:30:00"` |
| `created_by` | VARCHAR(100) | NULL | Account created by (user or 'system') | `"system"`, `"admin@va.gov"` |

#### Indexes

| Index Name | Columns | Type | Notes |
|------------|---------|------|-------|
| `idx_users_email` | `email` | B-tree | Login lookups |
| `idx_users_home_site` | `home_site_sta3n` | B-tree | Site-based queries |
| `idx_users_active` | `is_active` | B-tree | Active user filtering |

#### Constraints

- **Primary Key:** `user_id`
- **Unique:** `email`

**⚠️ Security Note:** The `password_hash` column contains bcrypt-hashed passwords. Never store plaintext passwords.

---

### Table: `auth.sessions`

**Purpose:** Active user sessions with timeout enforcement.

**Primary Key:** `session_id` (UUID)

**Source:** Application-managed (session creation on login)

#### Columns

| Column Name | Data Type | Nullable | Description | Example Values |
|-------------|-----------|----------|-------------|----------------|
| `session_id` | UUID | NOT NULL | Auto-generated session ID | `"7f3d8e2a-4b9c-1f5e-8a3d-9c7b6e5d4f3a"` |
| `user_id` | UUID | NOT NULL | User ID (foreign key to auth.users) | `"550e8400-e29b-41d4-a716-446655440000"` |
| `created_at` | TIMESTAMP | NULL | Session creation timestamp | `"2026-01-22 08:30:00"` |
| `last_activity_at` | TIMESTAMP | NULL | Last activity timestamp (updated on every request) | `"2026-01-22 09:15:00"` |
| `expires_at` | TIMESTAMP | NOT NULL | Session expiration timestamp (calculated as last_activity_at + timeout) | `"2026-01-22 09:40:00"` |
| `is_active` | BOOLEAN | NULL | Session is active | `true`, `false` |
| `ip_address` | VARCHAR(45) | NULL | Client IP address | `"10.0.1.100"`, `"2001:0db8:85a3::8a2e:0370:7334"` |
| `user_agent` | TEXT | NULL | Client user agent string | `"Mozilla/5.0..."` |

#### Indexes

| Index Name | Columns | Type | Notes |
|------------|---------|------|-------|
| `idx_sessions_user` | `user_id`, `is_active` | B-tree | User-based queries |
| `idx_sessions_expiry` | `expires_at`, `is_active` | B-tree | Expiration cleanup |
| `idx_sessions_activity` | `last_activity_at` | B-tree | Activity tracking |

#### Constraints

- **Primary Key:** `session_id`
- **Foreign Key:** `user_id` → `auth.users.user_id` (ON DELETE CASCADE)

---

### Table: `auth.audit_logs`

**Purpose:** Audit trail of all authentication events.

**Primary Key:** `audit_id` (auto-increment)

**Source:** Application-managed (automatic logging on auth events)

#### Columns

| Column Name | Data Type | Nullable | Description | Example Values |
|-------------|-----------|----------|-------------|----------------|
| `audit_id` | BIGSERIAL | NOT NULL | Auto-increment primary key | `1`, `2`, `3` |
| `user_id` | UUID | NULL | User ID (foreign key, NULL if login failed) | `"550e8400-e29b-41d4-a716-446655440000"`, `null` |
| `event_type` | VARCHAR(50) | NOT NULL | Event type | `"login"`, `"logout"`, `"login_failed"`, `"session_timeout"`, `"session_invalidated"` |
| `event_timestamp` | TIMESTAMP | NULL | Event timestamp | `"2026-01-22 08:30:00"` |
| `email` | VARCHAR(255) | NULL | Email address (for failed login tracking) | `"jane.doctor@va.gov"` |
| `ip_address` | VARCHAR(45) | NULL | Client IP address | `"10.0.1.100"` |
| `user_agent` | TEXT | NULL | Client user agent string | `"Mozilla/5.0..."` |
| `success` | BOOLEAN | NULL | Event success status | `true`, `false` |
| `failure_reason` | TEXT | NULL | Failure reason (for failed events) | `"Invalid password"`, `"Account locked"` |
| `session_id` | UUID | NULL | Associated session ID (if applicable) | `"7f3d8e2a-4b9c-1f5e-8a3d-9c7b6e5d4f3a"` |

#### Indexes

| Index Name | Columns | Type | Notes |
|------------|---------|------|-------|
| `idx_audit_user` | `user_id`, `event_timestamp DESC` | B-tree | User audit trail |
| `idx_audit_type` | `event_type`, `event_timestamp DESC` | B-tree | Event type filtering |
| `idx_audit_timestamp` | `event_timestamp DESC` | B-tree | Chronological queries |

#### Constraints

- **Primary Key:** `audit_id`
- **Foreign Key:** `user_id` → `auth.users.user_id` (ON DELETE SET NULL)

---

## Schema: `public` (AI Checkpoint Tables)

The `public` schema contains AI/ML infrastructure tables for LangGraph conversation memory. These tables are **auto-created** by LangGraph's `AsyncPostgresSaver.setup()` at application startup (no manual DDL execution required).

**⚠️ Important:** These tables use the `public` schema (LangGraph default) rather than a custom `ai` schema to avoid connection string complexity.

---

### Table: `public.checkpoints`

**Purpose:** LangGraph conversation state metadata for AI Clinical Insights feature (conversation memory persistence).

**Primary Key:** `(thread_id, checkpoint_id)` (composite)

**Source:** Auto-created by LangGraph `AsyncPostgresSaver.setup()` at application startup

#### Columns

| Column Name | Data Type | Nullable | Description | Example Values |
|-------------|-----------|----------|-------------|----------------|
| `thread_id` | TEXT | NOT NULL | Thread identifier (format: `{user_id}_{patient_icn}`) | `"550e8400_ICN100001"` |
| `checkpoint_id` | TEXT | NOT NULL | Unique checkpoint identifier (UUID v4) | `"9c8d7e6f-5a4b-3c2d-1e0f-9a8b7c6d5e4f"` |
| `parent_id` | TEXT | NULL | Previous checkpoint_id in conversation chain (null for first message) | `"8b7c6d5e-4f3a-2b1c-0d9e-8a7b6c5d4e3f"` |
| `metadata` | JSONB | NOT NULL | Conversation metadata (timestamps, configuration) | `{"timestamp": "2026-01-22T09:15:00Z"}` |

#### Indexes

Indexes are auto-created by LangGraph (specific names may vary by LangGraph version).

#### Constraints

- **Primary Key:** `(thread_id, checkpoint_id)`

**Usage Notes:**
- **Thread ID Format:** `{user_id}_{patient_icn}` for user+patient isolation (user-scoped, persists across login sessions)
- **Storage:** Lightweight metadata only (large data stored in `checkpoint_blobs`)
- **Lifecycle:** Persists across user logins; cleared manually via "Clear Chat History" button or on patient change
- **Auto-Created:** No manual DDL required - created by `AsyncPostgresSaver.setup()` at app startup

---

### Table: `public.checkpoint_writes`

**Purpose:** LangGraph checkpoint pending writes (internal LangGraph infrastructure for transactional updates).

**Primary Key:** `(thread_id, checkpoint_id, task_id, idx)` (composite)

**Source:** Auto-created by LangGraph `AsyncPostgresSaver.setup()` at application startup

#### Columns

| Column Name | Data Type | Nullable | Description | Example Values |
|-------------|-----------|----------|-------------|----------------|
| `thread_id` | TEXT | NOT NULL | Thread identifier | `"550e8400_ICN100001"` |
| `checkpoint_id` | TEXT | NOT NULL | Checkpoint identifier | `"9c8d7e6f-5a4b-3c2d-1e0f-9a8b7c6d5e4f"` |
| `task_id` | TEXT | NOT NULL | LangGraph task identifier for parallel execution tracking | `"task-001"` |
| `idx` | INTEGER | NOT NULL | Write index for ordering within a task | `0`, `1`, `2` |
| `channel` | TEXT | NOT NULL | LangGraph channel name | `"messages"`, `"tool_calls"`, `"intermediate_steps"` |
| `value` | JSONB | NULL | Pending write value (JSONB) | `{"type": "human", "content": "Hello"}` |

#### Indexes

Indexes are auto-created by LangGraph (specific names may vary by LangGraph version).

#### Constraints

- **Primary Key:** `(thread_id, checkpoint_id, task_id, idx)`

**Usage Notes:**
- **Internal Table:** Managed automatically by LangGraph AsyncPostgresSaver
- **Purpose:** Transactional checkpoint updates during agent execution
- **Auto-Created:** No manual DDL required

---

### Table: `public.checkpoint_blobs`

**Purpose:** Binary blob storage for large checkpoint data (performance optimization in LangGraph v3.x).

**Primary Key:** `(thread_id, checkpoint_id, channel)` (composite)

**Source:** Auto-created by LangGraph `AsyncPostgresSaver.setup()` at application startup

#### Columns

| Column Name | Data Type | Nullable | Description | Example Values |
|-------------|-----------|----------|-------------|----------------|
| `thread_id` | TEXT | NOT NULL | Thread identifier | `"550e8400_ICN100001"` |
| `checkpoint_id` | TEXT | NOT NULL | Checkpoint identifier | `"9c8d7e6f-5a4b-3c2d-1e0f-9a8b7c6d5e4f"` |
| `channel` | TEXT | NOT NULL | Channel name for blob storage | `"messages"`, `"state"` |
| `type` | TEXT | NULL | Blob type/format | `"json"`, `"pickle"` |
| `blob` | BYTEA | NULL | Binary blob data (compressed conversation state) | `\x1f8b08...` (gzipped data) |

#### Indexes

Indexes are auto-created by LangGraph (specific names may vary by LangGraph version).

#### Constraints

- **Primary Key:** `(thread_id, checkpoint_id, channel)`

**Usage Notes:**
- **Storage Optimization:** Large conversation data stored as binary blobs instead of JSONB
- **Typical Size:** ~50KB per conversation thread
- **Compression:** May use gzip or other compression
- **Auto-Created:** No manual DDL required

---

### Table: `public.checkpoint_migrations`

**Purpose:** LangGraph schema version tracking for database upgrades.

**Primary Key:** `v`

**Source:** Auto-created by LangGraph `AsyncPostgresSaver.setup()` at application startup

#### Columns

| Column Name | Data Type | Nullable | Description | Example Values |
|-------------|-----------|----------|-------------|----------------|
| `v` | INTEGER | NOT NULL | Schema version number | `1` (LangGraph v3.x) |

#### Constraints

- **Primary Key:** `v`

**Usage Notes:**
- **Version Tracking:** Ensures checkpoint schema compatibility across LangGraph upgrades
- **Current Version:** `v = 1` for LangGraph v3.x checkpoint schema
- **Auto-Created:** No manual DDL required
- **Read-Only:** Managed by LangGraph migration system

---

### AI Checkpoint Tables: Key Notes

**Auto-Creation:**
- All 4 checkpoint tables are **automatically created** by `AsyncPostgresSaver.setup()` at application startup
- No manual DDL execution is required
- Tables are created in the `public` schema (LangGraph default)
- Setup is idempotent (safe to run multiple times)

**Verification:**
```bash
# Verify checkpoint tables exist
docker exec -it postgres16 psql -U postgres -d medz1 -c "\dt public.*point*"

# Expected output: 4 tables
# - public.checkpoints
# - public.checkpoint_writes
# - public.checkpoint_blobs
# - public.checkpoint_migrations
```

**Thread ID Format:**
- Format: `{user_id}_{patient_icn}` (e.g., `"550e8400-e29b-41d4-a716-446655440000_ICN100001"`)
- Isolation: User-scoped + patient-scoped
- Persistence: Survives user logout/login (user-scoped conversation memory)
- Cleared: Manually via "Clear Chat History" button or automatically on patient change

**Storage Estimates:**
- ~50KB per conversation thread (typical)
- Stored primarily in `checkpoint_blobs` table (binary compressed data)
- Metadata in `checkpoints` table is lightweight

**Reference DDL:**
An optional reference DDL script exists at `db/ddl/create_ai_checkpoints_tables.sql` for documentation purposes only. This script is **NOT required** for normal operation - LangGraph creates the tables automatically.

**See Also:**
- `docs/spec/ai-insight-design.md` - Phase 6: Conversation Memory specification
- `docs/guide/developer-setup-guide.md` - PostgreSQL AI Infrastructure Setup section
- `app/main.py` - Lifespan handler with `AsyncPostgresSaver.setup()` call
- LangGraph AsyncPostgresSaver documentation

---

## Common Query Patterns

### Pattern 1: Get All Patient Data (Dashboard)

```sql
-- Get patient demographics
SELECT * FROM clinical.patient_demographics WHERE patient_key = 'ICN100001';

-- Get recent vitals (last 30 days)
SELECT * FROM clinical.patient_vitals
WHERE patient_key = 'ICN100001'
  AND taken_datetime >= NOW() - INTERVAL '30 days'
ORDER BY taken_datetime DESC;

-- Get active patient flags
SELECT * FROM clinical.patient_flags
WHERE patient_key = 'ICN100001'
  AND is_active = TRUE
ORDER BY assignment_date DESC;

-- Get active allergies
SELECT * FROM clinical.patient_allergies
WHERE patient_key = 'ICN100001'
  AND is_active = TRUE
ORDER BY severity_rank DESC, origination_date DESC;

-- Get active medications (outpatient)
SELECT * FROM clinical.patient_medications_outpatient
WHERE patient_icn = 'ICN100001'
  AND is_active = TRUE
ORDER BY issue_date DESC;

-- Get recent encounters (last 6 months)
SELECT * FROM clinical.patient_encounters
WHERE patient_key = 'ICN100001'
  AND admit_datetime >= NOW() - INTERVAL '6 months'
ORDER BY admit_datetime DESC;

-- Get recent labs (last 90 days)
SELECT * FROM clinical.patient_labs
WHERE patient_key = 'ICN100001'
  AND collection_datetime >= NOW() - INTERVAL '90 days'
ORDER BY collection_datetime DESC;

-- Get recent clinical notes (last 6 months)
SELECT * FROM clinical.patient_clinical_notes
WHERE patient_key = 'ICN100001'
  AND reference_datetime >= NOW() - INTERVAL '6 months'
ORDER BY reference_datetime DESC;

-- Get recent immunizations (last 2 years)
SELECT * FROM clinical.patient_immunizations
WHERE patient_key = 'ICN100001'
  AND administered_datetime >= NOW() - INTERVAL '2 years'
ORDER BY administered_datetime DESC;
```

### Pattern 2: Search Patients by Name/SSN

```sql
-- Search by last name
SELECT * FROM clinical.patient_demographics
WHERE name_last ILIKE 'DOOR%'
ORDER BY name_last, name_first;

-- Search by SSN last 4
SELECT * FROM clinical.patient_demographics
WHERE ssn_last4 = '6789';
```

### Pattern 3: Get Patient-Specific Clinical Domain Data

```sql
-- Get patient vitals with filtering
SELECT * FROM clinical.patient_vitals
WHERE patient_key = 'ICN100001'
  AND vital_type = 'BLOOD PRESSURE'
  AND taken_datetime >= NOW() - INTERVAL '1 year'
ORDER BY taken_datetime DESC;

-- Get patient medications by drug class
SELECT * FROM clinical.patient_medications_outpatient
WHERE patient_icn = 'ICN100001'
  AND drug_class = 'ANTIDIABETIC'
  AND is_active = TRUE
ORDER BY issue_date DESC;

-- Get patient labs by panel
SELECT * FROM clinical.patient_labs
WHERE patient_key = 'ICN100001'
  AND panel_name = 'Basic Metabolic Panel'
  AND collection_datetime >= NOW() - INTERVAL '1 year'
ORDER BY collection_datetime DESC;

-- Get patient clinical notes by document class
SELECT * FROM clinical.patient_clinical_notes
WHERE patient_key = 'ICN100001'
  AND document_class = 'Progress Notes'
  AND reference_datetime >= NOW() - INTERVAL '6 months'
ORDER BY reference_datetime DESC;

-- Get patient immunizations by vaccine group
SELECT i.*, v.vaccine_short_name, v.vaccine_group
FROM clinical.patient_immunizations i
LEFT JOIN reference.vaccine v ON i.cvx_code = v.cvx_code
WHERE i.patient_key = 'ICN100001'
  AND v.vaccine_group = 'COVID-19'
ORDER BY i.administered_datetime DESC;
```

### Pattern 4: Cross-Domain Joins

```sql
-- Get patient demographics with active flags
SELECT d.*, f.flag_name, f.flag_category, f.review_status
FROM clinical.patient_demographics d
LEFT JOIN clinical.patient_flags f ON d.patient_key = f.patient_key AND f.is_active = TRUE
WHERE d.patient_key = 'ICN100001';

-- Get patient allergies with reaction details
SELECT a.*, r.reaction_name
FROM clinical.patient_allergies a
LEFT JOIN clinical.patient_allergy_reactions r ON a.allergy_sid = r.allergy_sid
WHERE a.patient_key = 'ICN100001'
  AND a.is_active = TRUE
ORDER BY a.severity_rank DESC, a.origination_date DESC;

-- Get patient immunizations with CVX vaccine info
SELECT i.*, v.vaccine_short_name, v.vaccine_group, v.typical_series_pattern
FROM clinical.patient_immunizations i
LEFT JOIN reference.vaccine v ON i.cvx_code = v.cvx_code
WHERE i.patient_key = 'ICN100001'
ORDER BY i.administered_datetime DESC;
```

### Pattern 5: Aggregate Queries (Statistics)

```sql
-- Count active patients by station
SELECT primary_station, primary_station_name, COUNT(*) AS patient_count
FROM clinical.patient_demographics
WHERE deceased_flag IS NULL OR deceased_flag != 'Y'
GROUP BY primary_station, primary_station_name
ORDER BY patient_count DESC;

-- Count vitals by type (last 30 days)
SELECT vital_type, COUNT(*) AS vital_count
FROM clinical.patient_vitals
WHERE taken_datetime >= NOW() - INTERVAL '30 days'
GROUP BY vital_type
ORDER BY vital_count DESC;

-- Count active flags by category
SELECT flag_category, COUNT(*) AS flag_count
FROM clinical.patient_flags
WHERE is_active = TRUE
GROUP BY flag_category;

-- Count patient immunizations by vaccine group (last 2 years)
SELECT v.vaccine_group, COUNT(*) AS immunization_count
FROM clinical.patient_immunizations i
LEFT JOIN reference.vaccine v ON i.cvx_code = v.cvx_code
WHERE i.administered_datetime >= NOW() - INTERVAL '2 years'
GROUP BY v.vaccine_group
ORDER BY immunization_count DESC;
```

---

## Data Volume Estimates

### Typical Row Counts (Per Patient)

| Table | Typical Rows/Patient | Notes |
|-------|----------------------|-------|
| `patient_demographics` | 1 | One record per patient |
| `patient_vitals` | 50-500 | Varies by frequency of visits |
| `patient_flags` | 0-5 | Most patients have 0-2 active flags |
| `patient_flag_history` | 0-20 | Multiple history entries per flag |
| `patient_allergies` | 0-15 | Most patients have 2-10 allergies |
| `patient_allergy_reactions` | 0-30 | 1-3 reactions per allergy |
| `patient_medications_outpatient` | 5-50 | Active + historical prescriptions |
| `patient_medications_inpatient` | 0-100 | Only patients with inpatient stays |
| `patient_encounters` | 0-20 | Inpatient admissions only |
| `patient_labs` | 50-500 | Varies by patient complexity |
| `patient_clinical_notes` | 10-200 | Varies by frequency of care |
| `patient_immunizations` | 10-50 | Childhood + adult vaccinations |

### Estimated Storage (Per Patient)

| Table | Avg Size/Patient | Notes |
|-------|------------------|-------|
| `patient_demographics` | ~2 KB | Single record |
| `patient_vitals` | ~50-100 KB | 100 vitals @ 500 bytes each |
| `patient_flags` | ~2-5 KB | 2-3 active flags |
| `patient_flag_history` | ~5-10 KB | With narrative text |
| `patient_allergies` | ~5-10 KB | 5 allergies with reactions |
| `patient_medications_outpatient` | ~10-20 KB | 20 prescriptions |
| `patient_medications_inpatient` | ~5-50 KB | Varies by admissions |
| `patient_encounters` | ~5-10 KB | 5-10 encounters |
| `patient_labs` | ~20-50 KB | 100 labs @ 200 bytes each |
| `patient_clinical_notes` | ~100-500 KB | With full narrative text |
| `patient_immunizations` | ~10-20 KB | 20 immunizations |

**Total Per Patient:** ~200 KB - 1 MB (depending on care complexity and note volume)

### Database Size Estimates (100,000 Patients)

| Schema | Estimated Size | Notes |
|--------|----------------|-------|
| `clinical` | 20-100 GB | Clinical data (primary storage) |
| `reference` | <1 MB | CVX vaccine lookup table |
| `auth` | 10-50 MB | User accounts and sessions |
| `ai` | 100 MB - 1 GB | LangGraph checkpoints (active conversations only) |

**Total Database Size:** ~20-100 GB for 100,000 patients (excluding indexes and overhead)

---

## Notes for External Applications

### CCOW Testing Application

When building a simple EHR web app to test the med-z1 CCOW service:

1. **Patient Identity:** Use `patient_key` (ICN) as the primary patient identifier across all clinical tables.
2. **CCOW Integration:** Set patient context via `PUT /ccow/active-patient` with ICN.
3. **Data Retrieval:** Query clinical tables using ICN from CCOW context.
4. **Minimal Required Data:** For basic patient display, query:
   - `clinical.patient_demographics` (demographics)
   - `clinical.patient_vitals` (recent vitals)
   - `clinical.patient_allergies` (active allergies)
   - `clinical.patient_medications_outpatient` (active medications)
5. **Read-Only Access:** All clinical tables grant `SELECT` to `PUBLIC` (read-only).

### Performance Considerations

- **Index Usage:** All patient-centric queries are optimized with `(patient_key, date DESC)` indexes.
- **Pagination:** For large result sets (encounters, labs, notes), use `LIMIT` and `OFFSET` or cursor-based pagination.
- **Date Filtering:** Always include date range filters (`>= NOW() - INTERVAL '6 months'`) to limit result set size.
- **Join Strategy:** Use LEFT JOINs for optional relationships (e.g., `patient_allergies` → `patient_allergy_reactions`).

### Security Considerations

- **PHI/PII Protection:** Several columns contain sensitive data (see ⚠️ notes above):
  - `patient_demographics.ssn`
  - `patient_allergies.comment`
  - `patient_flag_history.history_comments`
  - `patient_clinical_notes.document_text`
  - `auth.users.password_hash`
- **Access Control:** Implement role-based access control (RBAC) in application layer.
- **Audit Logging:** Log all patient data access for HIPAA compliance.
- **Encryption:** Use SSL/TLS connections to PostgreSQL in production.

---

## Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| v1.0 | 2026-01-22 | Claude Code | Initial database reference documentation |
| v1.1 | 2026-01-22 | Claude Code | Corrected AI checkpoint tables: schema=`public` (not `ai`), 4 tables (not 2), auto-created by LangGraph |

---

**End of Document**
