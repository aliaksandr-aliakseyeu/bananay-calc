from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    # Supabase Free Tier: max 15 connections total
    # Conservative settings to avoid "max clients reached" error
    pool_size=2,  # Only 2 persistent connections
    max_overflow=3,  # Allow up to 3 temporary connections (total max = 5)
    pool_timeout=30,  # Wait 30 seconds for connection
    pool_recycle=300,  # Recycle connections after 5 minutes (was 1 hour)
    pool_pre_ping=True,  # Check connection health before using
    # Additional optimizations for Supabase
    connect_args={
        "statement_cache_size": 0,  # Disable prepared statements for Supabase/PgBouncer
        "prepared_statement_cache_size": 0,
        "timeout": 10,  # Connection timeout 10 seconds
        "server_settings": {
            "application_name": "bananay_calc_api",  # Track connections in Supabase dashboard
            "jit": "off",  # Disable JIT for faster small queries
        }
    }
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


async def get_db() -> AsyncSession:
    """Dependency for getting async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
