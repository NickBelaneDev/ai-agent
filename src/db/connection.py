from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from ..config.settings import env_settings

# 1. Erstelle die Engine (Der Motor)
# "check_same_thread": False ist speziell für SQLite wichtig

connect_args = {}
if "sqlite" in env_settings.DATABASE_URL:
    connect_args = {"check_same_thread": False}

engine = create_async_engine(
    env_settings.DATABASE_URL,
    connect_args=connect_args
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    from src.db.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)