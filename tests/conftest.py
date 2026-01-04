import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.db.models import Base
from src.db.connection import AsyncSessionLocal as ProductionAsyncSessionLocal # Import the production session for comparison if needed

# Setup for in-memory SQLite database for testing
@pytest.fixture(scope="session")
def event_loop():
    """Forces pytest-asyncio to use a session-scoped event loop."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def db_session():
    """
    Provides an asynchronous SQLAlchemy session for tests.
    Uses an in-memory SQLite database for isolation and speed.
    """
    # Create an in-memory SQLite engine
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create a sessionmaker for this engine
    TestingAsyncSessionLocal = async_sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with TestingAsyncSessionLocal() as session:
        yield session
        
        # Rollback all changes after each test to ensure a clean state
        await session.rollback()
    
    # Drop tables and dispose of the engine after all tests in the session are done
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
