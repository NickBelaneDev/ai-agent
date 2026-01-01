from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from src.config.settings import env_settings

# Create the async engine
engine = create_async_engine(
    env_settings.database_url,
    echo=False, # Set to True for SQL logging
)

# Create a session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    """Dependency for FastAPI routes to get a DB session."""
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    """Creates tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)