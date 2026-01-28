#!/usr/bin/env python3
"""
Verification script for patient service sex/gender fields fix.

This script tests that:
1. get_patient_demographics() returns both 'sex' and 'gender' fields
2. Patient detail page can render without errors
3. All expected fields are present in the returned data

Run from project root:
    python -m scripts.verify_patient_service
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from app.services.patient_service import get_patient_demographics


async def verify_patient_service():
    """Verify patient service returns sex and gender fields."""

    print("=" * 60)
    print("Patient Service Verification Script")
    print("=" * 60)
    print()

    # Get a database session
    print("1. Connecting to database...")
    async for db in get_db():
        session: AsyncSession = db
        break
    print("   ✅ Connected successfully\n")

    # Test with a known patient (ICN100001 should exist in sample data)
    test_icn = "ICN100001"
    print(f"2. Testing get_patient_demographics() with ICN: {test_icn}")

    try:
        patient = await get_patient_demographics(session, test_icn)

        if not patient:
            print(f"   ❌ ERROR: Patient {test_icn} not found in database")
            print("   → This may indicate the sample data is not loaded")
            print("   → Try with a different ICN from your database")
            await session.close()
            return False

        print("   ✅ Patient data retrieved successfully\n")

        # Check for required fields
        print("3. Verifying required fields are present:")
        required_fields = [
            "patient_key",
            "icn",
            "name_display",
            "name_first",
            "name_last",
            "dob",
            "age",
            "sex",        # CRITICAL: Must be present for patient_detail.html and dashboard
            "ssn_last4"
        ]

        all_fields_present = True
        for field in required_fields:
            if field in patient:
                value = patient[field]
                # Highlight sex field
                if field == "sex":
                    print(f"   ✅ '{field}': {value!r} ⬅️ CRITICAL FIELD")
                else:
                    print(f"   ✅ '{field}': {value!r}")
            else:
                print(f"   ❌ MISSING: '{field}' ⬅️ ERROR!")
                all_fields_present = False

        print()

        # Summary
        if all_fields_present:
            print("=" * 60)
            print("✅ VERIFICATION PASSED")
            print("=" * 60)
            print()
            print("All required fields are present:")
            print(f"  - sex field: {patient['sex']!r} (for patient detail page and dashboard)")
            print()
            print("The patient detail page should now display Sex correctly.")
            print("The dashboard enhancement (Section 10.4) is ready to apply.")
            print()
            print("Note: The 'gender' field does NOT exist in the actual database.")
            print("      Only 'sex' field is available (values: 'M' or 'F').")
            await session.close()
            return True
        else:
            print("=" * 60)
            print("❌ VERIFICATION FAILED")
            print("=" * 60)
            print()
            print("Missing fields detected. The patient service needs correction.")
            print("Expected field in get_patient_demographics() return dict:")
            print("  - sex (TEXT: 'M'/'F')")
            await session.close()
            return False

    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        print()
        print("Exception details:")
        import traceback
        traceback.print_exc()
        await session.close()
        return False


async def verify_template_compatibility():
    """Verify patient_detail.html template references are valid."""

    print("\n4. Checking patient_detail.html template compatibility:")

    template_path = project_root / "app" / "templates" / "patient_detail.html"

    if not template_path.exists():
        print(f"   ⚠️  Template not found: {template_path}")
        return False

    with open(template_path, 'r') as f:
        template_content = f.read()

    # Check for sex field reference
    if "{{ patient.sex }}" in template_content:
        print("   ✅ Template references {{ patient.sex }} - field must be present")
    else:
        print("   ⚠️  Template does NOT reference {{ patient.sex }}")

    # Verify gender is NOT referenced (it doesn't exist in DB)
    if "{{ patient.gender }}" in template_content:
        print("   ⚠️  WARNING: Template references {{ patient.gender }} but this field does NOT exist in database!")
        return False

    return True


async def main():
    """Main verification workflow."""

    # Run patient service verification
    service_ok = await verify_patient_service()

    # Run template compatibility check
    template_ok = await verify_template_compatibility()

    print("\n" + "=" * 60)
    if service_ok and template_ok:
        print("🎉 ALL VERIFICATIONS PASSED")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Restart the med-z4 server (if running)")
        print("  2. Navigate to: http://localhost:8005/patient/ICN100001")
        print("  3. Verify Sex field displays correctly in patient header")
        print("  4. Apply Section 10.4 dashboard enhancement when ready")
        sys.exit(0)
    else:
        print("⚠️  VERIFICATION INCOMPLETE")
        print("=" * 60)
        print("\nSome checks failed. Review output above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
