import pytest
import pytest_asyncio # Keep this if other async fixtures are used, otherwise can be removed
from sqlalchemy import select, text
from src.db.models import Base, ChatSession, User
from src.db.service import ChatSessionDBService
import time
import uuid
import json

# The test_engine and test_session fixtures are now provided by conftest.py

@pytest.mark.asyncio
async def test_chat_session_crud(db_session):
    """Test Create, Read, Update, Delete operations for ChatSession."""

    # 1. Create User first (Foreign Key constraint)
    user_name = "test_user"
    user = User(name=user_name)
    db_session.add(user)
    await db_session.commit()

    # 2. Create Session
    initial_history = '[{"role": "user", "parts": [{"text": "hi"}]}]'
    now = time.time()
    session_id = str(uuid.uuid4())
    
    new_session = ChatSession(
        session_id=session_id,
        user_name=user_name,
        history_json=initial_history,
        last_active=now
    )
    db_session.add(new_session)
    await db_session.commit()
    
    # 3. Read
    result = await db_session.execute(select(ChatSession).where(ChatSession.user_name == user_name))
    fetched_session = result.scalar_one_or_none()
    
    assert fetched_session is not None
    assert fetched_session.user_name == user_name
    assert fetched_session.history_json == initial_history
    assert fetched_session.last_active == pytest.approx(now)
    
    # 4. Update
    updated_history = '[{"role": "user", "parts": [{"text": "hi"}]}, {"role": "model", "parts": [{"text": "hello"}]}]'
    fetched_session.history_json = updated_history
    await db_session.commit()
    
    # Verify update
    result = await db_session.execute(select(ChatSession).where(ChatSession.user_name == user_name))
    updated_session = result.scalar_one()
    assert updated_session.history_json == updated_history
    
    # 5. Delete
    await db_session.delete(updated_session)
    await db_session.commit()
    
    # Verify delete
    result = await db_session.execute(select(ChatSession).where(ChatSession.user_name == user_name))
    deleted_session = result.scalar_one_or_none()
    assert deleted_session is None

@pytest.mark.asyncio
async def test_chat_session_defaults(db_session):
    """Test default values for ChatSession."""
    user_name = "default_user"
    user = User(name=user_name)
    db_session.add(user)
    await db_session.commit()

    now = time.time()
    session_id = str(uuid.uuid4())
    
    # Only providing required fields
    new_session = ChatSession(
        session_id=session_id,
        user_name=user_name,
        last_active=now
    )
    db_session.add(new_session)
    await db_session.commit()
    
    result = await db_session.execute(select(ChatSession).where(ChatSession.user_name == user_name))
    fetched_session = result.scalar_one()
    
    # Check default value for history_json
    assert fetched_session.history_json == "[]"

@pytest.mark.asyncio
async def test_connection_check(db_session):
    """Test that the database connection is actually working."""
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1

@pytest.mark.asyncio
async def test_db_service_get_or_create_user(db_session):
    service = ChatSessionDBService(db_session)
    user_name = "service_user"
    
    # First call: Create
    user1 = await service.get_or_create_user(user_name)
    await service.commit()
    assert user1.name == user_name
    
    # Second call: Get
    user2 = await service.get_or_create_user(user_name)
    assert user2.name == user_name
    
    # Verify only one user exists
    result = await db_session.execute(select(User).where(User.name == user_name))
    users = result.scalars().all()
    assert len(users) == 1

@pytest.mark.asyncio
async def test_db_service_create_session(db_session):
    service = ChatSessionDBService(db_session)
    user_name = "session_user"
    
    # Create session (should implicitly create user)
    session = await service.create_session(user_name)
    await service.commit()
    
    assert session.user_name == user_name
    assert session.session_id is not None
    assert session.history_json == "[]"
    
    # Verify user was created
    user = await service.get_or_create_user(user_name)
    assert user is not None

@pytest.mark.asyncio
async def test_db_service_get_session(db_session):
    service = ChatSessionDBService(db_session)
    user_name = "get_session_user"
    
    # Create two sessions
    s1 = await service.create_session(user_name)
    # Sleep briefly to ensure different timestamps
    # (In tests with fast execution, timestamps might be identical otherwise)
    s1.last_active -= 100
    await service.commit()
    
    s2 = await service.create_session(user_name)
    await service.commit()
    
    # Get by ID
    fetched_s1 = await service.get_session(session_id=s1.session_id, user_name=user_name) # Added user_name for security check
    assert fetched_s1.session_id == s1.session_id
    
    # Get latest by user
    latest = await service.get_session(user_name=user_name)
    assert latest.session_id == s2.session_id

@pytest.mark.asyncio
async def test_db_service_update_session(db_session):
    service = ChatSessionDBService(db_session)
    user_name = "update_user"
    session = await service.create_session(user_name)
    await service.commit()
    
    new_history = [{"role": "user", "parts": [{"text": "test"}]}]
    token_usage = 10
    
    await service.update_session(session, new_history, token_usage)
    await service.commit()
    
    # Verify update
    updated = await service.get_session(session_id=session.session_id, user_name=user_name) # Added user_name for security check
    assert json.loads(updated.history_json) == new_history
    assert updated.token_count == 10
    
    # Update again (accumulate tokens)
    await service.update_session(session, [], 5)
    await service.commit()
    
    updated_again = await service.get_session(session_id=session.session_id, user_name=user_name) # Added user_name for security check
    assert updated_again.token_count == 15