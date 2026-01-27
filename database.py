# -----------------------------------------------------------
# database.py
# -----------------------------------------------------------
# Database connection management for med-z4
# Uses SQLAlchemy 2.x async with connection pooling
# -----------------------------------------------------------

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator
import logging

from  config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Async Database Engine (Singleton)
# ---------------------------------------------------------------------

engine = create_async_engine(
    settings.postgres.database_url,
    echo=settings.app.debug,         # Log SQL queries if debug=True
    pool_pre_ping=True,              # Verify connections before use
)

# Async session factory (creates new AsyncSession objects)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# ---------------------------------------------------------------------
# Session Dependency for FastAPI
# ---------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.

    Usage in routes:
        @app.get("/patients")
        async def list_patients(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Patient))
            patients = result.scalars().all()
            return patients
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()