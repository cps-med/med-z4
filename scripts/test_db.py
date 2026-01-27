# test_db.py

import asyncio
from sqlalchemy import text
from database import engine


async def test_connection():
    """Test database connectivity."""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✓ Database connected successfully!")
            print(f"  Result: {result.scalar()}")

            # Test querying a table
            result = await conn.execute(
                text("SELECT COUNT(*) FROM clinical.patient_demographics")
            )
            count = result.scalar()
            print(f"✓ Found {count} patients in database")

    except Exception as e:
        print(f"✗ Database connection failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_connection())