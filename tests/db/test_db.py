import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, text
from src.db.models import Base, ChatSession
import time

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    yield engine
    
    # Drop tables (cleanup)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest_asyncio.fixture
async def test_session(test_engine):
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session

@pytest.mark.asyncio
async def test_chat_session_crud(test_session):
    """Test Create, Read, Update, Delete operations for ChatSession."""
    
    # 1. Create
    user_name = "test_user"
    initial_history = '[{"role": "user", "parts": [{"text": "hi"}]}]'
    now = time.time()
    
    new_session = ChatSession(
        user_name=user_name,
        history_json=initial_history,
        last_active=now
    )
    test_session.add(new_session)
    await test_session.commit()
    
    # 2. Read
    result = await test_session.execute(select(ChatSession).where(ChatSession.user_name == user_name))
    fetched_session = result.scalar_one_or_none()
    
    assert fetched_session is not None
    assert fetched_session.user_name == user_name
    assert fetched_session.history_json == initial_history
    assert fetched_session.last_active == pytest.approx(now)
    
    # 3. Update
    updated_history = '[{"role": "user", "parts": [{"text": "hi"}]}, {"role": "model", "parts": [{"text": "hello"}]}]'
    fetched_session.history_json = updated_history
    await test_session.commit()
    
    # Verify update
    result = await test_session.execute(select(ChatSession).where(ChatSession.user_name == user_name))
    updated_session = result.scalar_one()
    assert updated_session.history_json == updated_history
    
    # 4. Delete
    await test_session.delete(updated_session)
    await test_session.commit()
    
    # Verify delete
    result = await test_session.execute(select(ChatSession).where(ChatSession.user_name == user_name))
    deleted_session = result.scalar_one_or_none()
    assert deleted_session is None

@pytest.mark.asyncio
async def test_chat_session_defaults(test_session):
    """Test default values for ChatSession."""
    user_name = "default_user"
    now = time.time()
    
    # Only providing required fields
    new_session = ChatSession(
        user_name=user_name,
        last_active=now
    )
    test_session.add(new_session)
    await test_session.commit()
    
    result = await test_session.execute(select(ChatSession).where(ChatSession.user_name == user_name))
    fetched_session = result.scalar_one()
    
    # Check default value for history_json
    assert fetched_session.history_json == "[]"

@pytest.mark.asyncio
async def test_connection_check(test_session):
    """Test that the database connection is actually working."""
    result = await test_session.execute(text("SELECT 1"))
    assert result.scalar() == 1
