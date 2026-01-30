# -----------------------------------------------------------
# app/services/patient_crud_service.py
# -----------------------------------------------------------
# Patient demographics CRUD operations service
# -----------------------------------------------------------

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any, Optional
from datetime import datetime, timezone, date
import logging

logger = logging.getLogger(__name__)


async def generate_next_icn(db: AsyncSession) -> str:
    """
    Generate next available ICN in the 999 series.
    Returns ICN in format: ICN999001, ICN999002, etc.
    """
    try:
        result = await db.execute(text(
            "SELECT MAX(icn) FROM clinical.patient_demographics WHERE icn LIKE 'ICN999%'"
        ))
        max_icn = result.scalar()

        if max_icn:
            # Extract number: "ICN999042" -> 999042
            current_num = int(max_icn.replace("ICN", ""))
            next_num = current_num + 1
        else:
            # First patient in 999 series
            next_num = 999001

        # Check if we've exhausted the series
        if next_num > 999999:
            raise ValueError("ICN 999 series exhausted (max: ICN999999)")

        return f"ICN{next_num:06d}"

    except Exception as e:
        logger.error(f"Error generating ICN: {e}")
        raise


async def create_patient(db: AsyncSession, patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new patient record.
    Auto-generates ICN, patient_key, name_display, age, and timestamps.
    """
    try:
        # Generate ICN
        icn = await generate_next_icn(db)

        # Calculate age from DOB
        age = None
        if patient_data.get("dob"):
            dob = datetime.fromisoformat(patient_data["dob"])
            today = datetime.now()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        # Generate name_display
        name_last = patient_data.get("name_last", "")
        name_first = patient_data.get("name_first", "")
        name_display = f"{name_last.upper()}, {name_first.capitalize()}" if name_last and name_first else ""

        # Extract last 4 of SSN if full SSN provided
        ssn_last4 = patient_data.get("ssn_last4")
        if not ssn_last4 and patient_data.get("ssn"):
            ssn_last4 = patient_data["ssn"].replace("-", "")[-4:]

        # Convert date strings to date objects for database
        dob_date = datetime.fromisoformat(patient_data["dob"]).date() if patient_data.get("dob") else None
        death_date_obj = datetime.fromisoformat(patient_data["death_date"]).date() if patient_data.get("death_date") else None

        # Prepare INSERT statement
        insert_query = text("""
            INSERT INTO clinical.patient_demographics (
                patient_key, icn, ssn, ssn_last4,
                name_last, name_first, name_display,
                dob, age, sex,
                primary_station, primary_station_name,
                address_street1, address_street2, address_city, address_state, address_zip,
                phone_primary, insurance_company_name,
                marital_status, religion, service_connected_percent,
                deceased_flag, death_date,
                source_system, last_updated
            ) VALUES (
                :patient_key, :icn, :ssn, :ssn_last4,
                :name_last, :name_first, :name_display,
                :dob, :age, :sex,
                :primary_station, :primary_station_name,
                :address_street1, :address_street2, :address_city, :address_state, :address_zip,
                :phone_primary, :insurance_company_name,
                :marital_status, :religion, :service_connected_percent,
                :deceased_flag, :death_date,
                :source_system, :last_updated
            )
        """)

        # Execute insert
        await db.execute(insert_query, {
            "patient_key": icn,  # patient_key same as ICN
            "icn": icn,
            "ssn": patient_data.get("ssn"),
            "ssn_last4": ssn_last4,
            "name_last": name_last,
            "name_first": name_first,
            "name_display": name_display,
            "dob": dob_date,
            "age": age,
            "sex": patient_data.get("sex"),
            "primary_station": patient_data.get("primary_station"),
            "primary_station_name": patient_data.get("primary_station_name"),
            "address_street1": patient_data.get("address_street1"),
            "address_street2": patient_data.get("address_street2"),
            "address_city": patient_data.get("address_city"),
            "address_state": patient_data.get("address_state"),
            "address_zip": patient_data.get("address_zip"),
            "phone_primary": patient_data.get("phone_primary"),
            "insurance_company_name": patient_data.get("insurance_company_name"),
            "marital_status": patient_data.get("marital_status"),
            "religion": patient_data.get("religion"),
            "service_connected_percent": patient_data.get("service_connected_percent"),
            "deceased_flag": patient_data.get("deceased_flag"),
            "death_date": death_date_obj,
            "source_system": "med-z4",
            "last_updated": datetime.now(timezone.utc)
        })

        await db.commit()

        return {
            "success": True,
            "icn": icn,
            "name_display": name_display
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating patient: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def update_patient(db: AsyncSession, icn: str, patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update existing patient record.
    Recalculates age and name_display if relevant fields changed.
    """
    try:
        # Calculate age from DOB if provided
        age = None
        if patient_data.get("dob"):
            dob = datetime.fromisoformat(patient_data["dob"])
            today = datetime.now()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        # Generate name_display if name fields provided
        name_display = None
        if patient_data.get("name_last") and patient_data.get("name_first"):
            name_last = patient_data["name_last"]
            name_first = patient_data["name_first"]
            name_display = f"{name_last.upper()}, {name_first.capitalize()}"

        # Extract last 4 of SSN if full SSN provided
        ssn_last4 = patient_data.get("ssn_last4")
        if not ssn_last4 and patient_data.get("ssn"):
            ssn_last4 = patient_data["ssn"].replace("-", "")[-4:]

        # Build UPDATE statement dynamically based on provided fields
        update_fields = []
        params = {"icn": icn}

        for field in ["ssn", "name_last", "name_first", "sex",
                      "primary_station", "primary_station_name",
                      "address_street1", "address_street2", "address_city", "address_state", "address_zip",
                      "phone_primary", "insurance_company_name",
                      "marital_status", "religion", "service_connected_percent",
                      "deceased_flag"]:
            if field in patient_data:
                update_fields.append(f"{field} = :{field}")
                params[field] = patient_data[field]

        # Handle date fields separately - convert strings to date objects
        if "dob" in patient_data and patient_data["dob"]:
            update_fields.append("dob = :dob")
            params["dob"] = datetime.fromisoformat(patient_data["dob"]).date()

        if "death_date" in patient_data and patient_data["death_date"]:
            update_fields.append("death_date = :death_date")
            params["death_date"] = datetime.fromisoformat(patient_data["death_date"]).date()

        # Add calculated/derived fields
        if age is not None:
            update_fields.append("age = :age")
            params["age"] = age

        if name_display is not None:
            update_fields.append("name_display = :name_display")
            params["name_display"] = name_display

        if ssn_last4:
            update_fields.append("ssn_last4 = :ssn_last4")
            params["ssn_last4"] = ssn_last4

        # Always update last_updated
        update_fields.append("last_updated = :last_updated")
        params["last_updated"] = datetime.now(timezone.utc)

        if not update_fields:
            return {"success": False, "error": "No fields to update"}

        update_query = text(f"""
            UPDATE clinical.patient_demographics
            SET {", ".join(update_fields)}
            WHERE icn = :icn
        """)

        result = await db.execute(update_query, params)
        await db.commit()

        if result.rowcount == 0:
            return {"success": False, "error": "Patient not found"}

        return {
            "success": True,
            "icn": icn,
            "name_display": name_display or "Patient"
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating patient {icn}: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def delete_patient(db: AsyncSession, icn: str) -> Dict[str, Any]:
    """
    Hard delete patient record with cascading delete of all clinical data.
    WARNING: This permanently removes the patient and ALL associated clinical records.

    Cascade order:
    1. Delete from all clinical tables (vitals, allergies, medications, etc.)
    2. Delete from patient_demographics
    """
    try:
        logger.info(f"Starting delete operation for patient: {icn}")

        # First verify patient exists
        check_query = text("""
            SELECT icn FROM clinical.patient_demographics WHERE icn = :icn
        """)
        result = await db.execute(check_query, {"icn": icn})
        if not result.fetchone():
            logger.warning(f"Delete failed: Patient {icn} not found")
            return {"success": False, "error": "Patient not found"}

        # Cascade delete from all clinical tables (using patient_key = icn)
        # Use defensive approach: try each table but don't fail if table doesn't exist
        clinical_tables = [
            "patient_vitals",
            "patient_flags",
            "patient_flag_history",
            "patient_allergies",
            "patient_allergy_reactions",
            "patient_medications_outpatient",
            "patient_medications_inpatient",
            "patient_encounters",
            "patient_labs",
            "patient_clinical_notes",
            "patient_immunizations"
        ]

        deleted_counts = {}
        for table in clinical_tables:
            try:
                delete_query = text(f"""
                    DELETE FROM clinical.{table}
                    WHERE patient_key = :patient_key
                """)
                result = await db.execute(delete_query, {"patient_key": icn})
                deleted_counts[table] = result.rowcount
            except Exception as table_error:
                # Log but continue - table might not exist or have different structure
                logger.warning(f"Could not delete from clinical.{table}: {table_error}")
                deleted_counts[table] = f"error: {str(table_error)}"

        # Finally, delete the patient demographics record
        logger.info(f"Deleting patient demographics for {icn}")
        delete_patient_query = text("""
            DELETE FROM clinical.patient_demographics
            WHERE icn = :icn
        """)
        result = await db.execute(delete_patient_query, {"icn": icn})
        demographics_deleted = result.rowcount

        logger.info(f"Demographics rows deleted: {demographics_deleted}")
        logger.info(f"Committing transaction for patient delete: {icn}")
        await db.commit()

        logger.info(f"✅ Patient deleted successfully: {icn} (cascade deleted: {deleted_counts})")

        return {"success": True, "icn": icn, "cascade_deleted": deleted_counts}

    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting patient {icn}: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def get_patient_by_icn(db: AsyncSession, icn: str) -> Optional[Dict[str, Any]]:
    """
    Fetch single patient by ICN for edit form population.
    """
    try:
        query = text("""
            SELECT * FROM clinical.patient_demographics
            WHERE icn = :icn
        """)

        result = await db.execute(query, {"icn": icn})
        row = result.fetchone()

        if not row:
            return None

        # Convert row to dict
        return dict(row._mapping)

    except Exception as e:
        logger.error(f"Error fetching patient {icn}: {e}")
        return None


def validate_patient_data(data: Dict[str, Any], is_create: bool = True) -> Dict[str, str]:
    """
    Validate patient data.
    Returns dict of field errors (empty if valid).
    """
    errors = {}

    # Required fields (based on database schema NOT NULL constraints)
    if is_create or "name_last" in data:
        if not data.get("name_last"):
            errors["name_last"] = "Last name is required"

    if is_create or "name_first" in data:
        if not data.get("name_first"):
            errors["name_first"] = "First name is required"

    if is_create or "dob" in data:
        if not data.get("dob"):
            errors["dob"] = "Date of birth is required"
        else:
            try:
                dob = datetime.fromisoformat(data["dob"])
                if dob > datetime.now():
                    errors["dob"] = "Date of birth cannot be in the future"

                # Check reasonable age range
                age = datetime.now().year - dob.year
                if age < 0 or age > 150:
                    errors["dob"] = "Date of birth results in unreasonable age"
            except ValueError:
                errors["dob"] = "Invalid date format"

    if is_create or "sex" in data:
        if not data.get("sex"):
            errors["sex"] = "Sex is required"
        elif data["sex"] not in ["M", "F"]:
            errors["sex"] = "Sex must be M or F"

    # Format validations (if provided)
    if data.get("ssn"):
        ssn = data["ssn"]
        if len(ssn) != 11 or ssn[3] != "-" or ssn[6] != "-":
            errors["ssn"] = "SSN must be in format ###-##-####"

    if data.get("phone_primary"):
        phone = data["phone_primary"]
        if len(phone) != 12 or phone[3] != "-" or phone[7] != "-":
            errors["phone_primary"] = "Phone must be in format ###-###-####"

    if data.get("address_zip"):
        zip_code = data["address_zip"]
        if not (len(zip_code) == 5 or (len(zip_code) == 10 and zip_code[5] == "-")):
            errors["address_zip"] = "ZIP must be ##### or #####-####"

    if data.get("address_state"):
        state = data["address_state"]
        if len(state) != 2 or not state.isupper():
            errors["address_state"] = "State must be 2-letter abbreviation (e.g., GA, CA)"

    if data.get("service_connected_percent"):
        try:
            percent = float(data["service_connected_percent"])
            if percent < 0 or percent > 100:
                errors["service_connected_percent"] = "Service connected percent must be 0-100"
        except ValueError:
            errors["service_connected_percent"] = "Must be a number"

    if data.get("death_date"):
        if not data.get("dob"):
            # Can't validate without DOB
            pass
        else:
            try:
                death_date = datetime.fromisoformat(data["death_date"])
                dob = datetime.fromisoformat(data["dob"])
                if death_date < dob:
                    errors["death_date"] = "Death date cannot be before birth date"
                if death_date > datetime.now():
                    errors["death_date"] = "Death date cannot be in the future"
            except ValueError:
                errors["death_date"] = "Invalid date format"

    return errors
