# -----------------------------------------------------------
# app/services/patient_service.py
# -----------------------------------------------------------
# Patient data service functions
# -----------------------------------------------------------

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


async def get_patient_demographics(db: AsyncSession, icn: str) -> Optional[Dict[str, Any]]:
    """
    Fetch patient demographics by ICN.
    Returns patient info dict or None if not found.
    """
    query = text("""
        SELECT
            patient_key,
            icn,
            name_display,
            name_first,
            name_last,
            dob,
            age,
            sex,
            ssn_last4
        FROM clinical.patient_demographics
        WHERE icn = :icn
    """)

    result = await db.execute(query, {"icn": icn})
    row = result.fetchone()

    if not row:
        logger.warning(f"Patient not found: {icn}")
        return None

    return {
        "patient_key": row[0],
        "icn": row[1],
        "name_display": row[2],
        "name_first": row[3],
        "name_last": row[4],
        "dob": row[5].strftime("%Y-%m-%d") if row[5] else "N/A",
        "age": row[6] if row[6] else "N/A",
        "sex": row[7] if row[7] else "Unknown",
        "ssn_last4": row[8] if row[8] else "N/A",
    }


async def get_patient_vitals(db: AsyncSession, patient_key: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch recent vitals for a patient.
    Returns list of vital sign dictionaries.
    """
    query = text("""
        SELECT
            vital_type,
            vital_abbr,
            taken_datetime,
            result_value,
            numeric_value,
            systolic,
            diastolic,
            unit_of_measure,
            location_name,
            abnormal_flag
        FROM clinical.patient_vitals
        WHERE patient_key = :patient_key
        ORDER BY taken_datetime DESC
        LIMIT :limit
    """)

    result = await db.execute(query, {"patient_key": patient_key, "limit": limit})

    vitals = []
    for row in result.fetchall():
        vitals.append({
            "vital_type": row[0],
            "vital_abbr": row[1],
            "taken_datetime": row[2].strftime("%Y-%m-%d %H:%M") if row[2] else "N/A",
            "result_value": row[3] if row[3] else "N/A",
            "numeric_value": float(row[4]) if row[4] else None,
            "systolic": row[5],
            "diastolic": row[6],
            "unit_of_measure": row[7] if row[7] else "",
            "location_name": row[8] if row[8] else "N/A",
            "abnormal_flag": row[9] if row[9] else "NORMAL",
        })

    return vitals


async def get_patient_allergies(db: AsyncSession, patient_key: str) -> List[Dict[str, Any]]:
    """
    Fetch active allergies for a patient.
    Returns list of allergy dictionaries.
    """
    query = text("""
        SELECT
            allergen_standardized,
            allergen_type,
            severity,
            reactions,
            origination_date,
            historical_or_observed
        FROM clinical.patient_allergies
        WHERE patient_key = :patient_key
          AND is_active = TRUE
        ORDER BY severity_rank DESC, origination_date DESC
    """)

    result = await db.execute(query, {"patient_key": patient_key})

    allergies = []
    for row in result.fetchall():
        allergies.append({
            "allergen": row[0],
            "type": row[1] if row[1] else "N/A",
            "severity": row[2] if row[2] else "Unknown",
            "reactions": row[3] if row[3] else "N/A",
            "origination_date": row[4].strftime("%Y-%m-%d") if row[4] else "N/A",
            "historical_or_observed": row[5] if row[5] else "N/A",
        })

    return allergies


async def get_patient_medications(db: AsyncSession, patient_key: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Fetch active outpatient medications for a patient.
    Returns list of medication dictionaries.
    """
    query = text("""
        SELECT
            drug_name_local,
            generic_name,
            drug_strength,
            sig,
            rx_status_computed,
            issue_date,
            expiration_date,
            refills_remaining,
            provider_name
        FROM clinical.patient_medications_outpatient
        WHERE patient_key = :patient_key
          AND is_active = TRUE
        ORDER BY issue_date DESC
        LIMIT :limit
    """)

    result = await db.execute(query, {"patient_key": patient_key, "limit": limit})

    medications = []
    for row in result.fetchall():
        medications.append({
            "drug_name": row[0] if row[0] else "N/A",
            "generic_name": row[1] if row[1] else "N/A",
            "strength": row[2] if row[2] else "N/A",
            "sig": row[3] if row[3] else "N/A",
            "status": row[4] if row[4] else "N/A",
            "issue_date": row[5].strftime("%Y-%m-%d") if row[5] else "N/A",
            "expiration_date": row[6].strftime("%Y-%m-%d") if row[6] else "N/A",
            "refills_remaining": row[7] if row[7] is not None else "N/A",
            "provider": row[8] if row[8] else "N/A",
        })

    return medications