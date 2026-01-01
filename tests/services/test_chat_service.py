import pytest
import asyncio
import json
import time
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from src.services.chat_service import SmartGeminiBackend
from src.db.models import Base, ChatSession
from src.config.settings import TIMEOUT_SECONDS

# --- Fixtures ---

@pytest.fixture
def mock_genai_client():
    client = MagicMock()
    client.chats.create = MagicMock()
    return client

@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.client = MagicMock()
    agent.client.chats.create = MagicMock()
    agent.process_chat_turn = AsyncMock()
    agent.ask = AsyncMock()
    return agent

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    # session.add is synchronous in SQLAlchemy, so we use MagicMock
    session.add = MagicMock()
    # Important: Ensure async context manager returns the session itself
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    return session

@pytest.fixture
def backend(mock_genai_client, mock_agent):
    # We patch load_config and GenericAgent to avoid real initialization
    with patch("src.services.chat_service.load_config") as mock_load_config, \
         patch("src.services.chat_service.GenericAgent", return_value=mock_agent), \
         patch("src.services.chat_service.genai.Client", return_value=mock_genai_client), \
         patch("src.services.chat_service.AgentToolRegistry"):
        
        mock_config = MagicMock()
        mock_config.model = "test-model"
        mock_config.system_instruction = "sys"
        mock_config.temperature = 0.5
        mock_config.max_output_tokens = 100
        mock_load_config.return_value = mock_config
        
        backend = SmartGeminiBackend("fake_key")
        return backend

# --- Tests ---

@pytest.mark.asyncio
async def test_generate_content(backend):
    """Test simple one-off generation."""
    backend.agent.ask.return_value = "Generated text"
    response = await backend.generate_content("Prompt")
    
    assert response == "Generated text"
    backend.agent.ask.assert_called_once_with("Prompt")

@pytest.mark.asyncio
async def test_chat_new_user(backend):
    """Test chat flow for a new user (no history)."""
    user_name = "new_user"
    prompt = "Hello"
    
    # Mock DB: No existing session
    mock_db = AsyncMock()
    # Ensure context manager returns the mock itself
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = None
    # Configure add as synchronous
    mock_db.add = MagicMock()
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    # Mock Agent response
    backend.agent.process_chat_turn.return_value = "Hi there"
    
    # Mock Chat object history
    mock_chat_obj = MagicMock()
    mock_chat_obj.history = [{"role": "user", "parts": [{"text": "Hello"}]}, {"role": "model", "parts": [{"text": "Hi there"}]}]
    backend.agent.client.chats.create.return_value = mock_chat_obj

    with patch("src.services.chat_service.AsyncSessionLocal", return_value=mock_db):
        response = await backend.chat(user_name, prompt)
    
    assert response == "Hi there"
    
    # Verify DB interaction
    mock_db.add.assert_called_once() # Should add new session
    mock_db.commit.assert_called_once()
    
    # Verify Agent interaction
    backend.agent.client.chats.create.assert_called_once()
    call_kwargs = backend.agent.client.chats.create.call_args.kwargs
    assert call_kwargs['history'] == [] # Empty history for new user

@pytest.mark.asyncio
async def test_chat_existing_user_active(backend):
    """Test chat flow for an existing user with an active session."""
    user_name = "active_user"
    prompt = "How are you?"
    
    # Mock DB: Existing active session
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = None
    mock_db.add = MagicMock()
    
    existing_session = ChatSession(
        user_name=user_name,
        history_json='[{"role": "user", "parts": [{"text": "prev"}]}]',
        last_active=time.time() # Just now
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_session
    mock_db.execute.return_value = mock_result
    
    # Mock Agent response
    backend.agent.process_chat_turn.return_value = "I am good"
    
    # Mock Chat object
    mock_chat_obj = MagicMock()
    mock_chat_obj.history = [] # Simplified for this test
    backend.agent.client.chats.create.return_value = mock_chat_obj

    with patch("src.services.chat_service.AsyncSessionLocal", return_value=mock_db):
        response = await backend.chat(user_name, prompt)
    
    assert response == "I am good"
    
    # Verify Agent interaction
    backend.agent.client.chats.create.assert_called_once()
    call_kwargs = backend.agent.client.chats.create.call_args.kwargs
    # Should have loaded history
    assert len(call_kwargs['history']) == 1 
    assert call_kwargs['history'][0]['role'] == 'user'

@pytest.mark.asyncio
async def test_chat_existing_user_expired(backend):
    """Test chat flow for an existing user whose session has expired."""
    user_name = "expired_user"
    prompt = "New topic"
    
    # Mock DB: Existing expired session
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = None
    mock_db.add = MagicMock()
    
    existing_session = ChatSession(
        user_name=user_name,
        history_json='[{"role": "user", "parts": [{"text": "old stuff"}]}]',
        last_active=time.time() - (TIMEOUT_SECONDS + 100) # Expired
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_session
    mock_db.execute.return_value = mock_result
    
    # Mock Agent response
    backend.agent.process_chat_turn.return_value = "Sure"
    
    # Mock Chat object
    mock_chat_obj = MagicMock()
    mock_chat_obj.history = []
    backend.agent.client.chats.create.return_value = mock_chat_obj

    with patch("src.services.chat_service.AsyncSessionLocal", return_value=mock_db):
        response = await backend.chat(user_name, prompt)
    
    assert response == "Sure"
    
    # Verify Agent interaction
    backend.agent.client.chats.create.assert_called_once()
    call_kwargs = backend.agent.client.chats.create.call_args.kwargs
    # Should have EMPTY history because session expired
    assert call_kwargs['history'] == []

@pytest.mark.asyncio
async def test_chat_concurrent_users(backend):
    """Test multiple users chatting concurrently."""
    user1 = "user1"
    user2 = "user2"
    
    # We need a side_effect for the DB session to return different mock sessions or handle concurrency
    # Since AsyncSessionLocal is a context manager, we mock it to return a new mock DB session each time
    
    async def chat_simulation(user, prompt, response_text):
        # Create a fresh mock DB for this call
        mock_db = AsyncMock()
        mock_db.__aenter__.return_value = mock_db
        mock_db.__aexit__.return_value = None
        mock_db.add = MagicMock()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None # Treat as new user for simplicity
        mock_db.execute.return_value = mock_result
        
        # Mock agent response for this specific call
        # We can't easily change the agent mock per call in parallel, 
        # so we'll rely on the return value being what we expect if the logic holds.
        # Instead, let's mock process_chat_turn to return the response_text passed in.
        
        # NOTE: In a real concurrent test with a shared mock, we'd need more complex setup.
        # Here we verify that the method can be awaited concurrently.
        
        with patch("src.services.chat_service.AsyncSessionLocal", return_value=mock_db):
             # We patch process_chat_turn locally if possible, or assume the shared mock returns something generic
             # Let's make the shared mock return the prompt as an echo to distinguish
             backend.agent.process_chat_turn.side_effect = lambda chat, p: f"Echo: {p}"
             
             return await backend.chat(user, prompt)

    # Run two chats concurrently
    results = await asyncio.gather(
        chat_simulation(user1, "Hello from 1", "Echo: Hello from 1"),
        chat_simulation(user2, "Hello from 2", "Echo: Hello from 2")
    )
    
    assert results[0] == "Echo: Hello from 1"
    assert results[1] == "Echo: Hello from 2"
    
    # Verify that create_chat was called twice (once for each user)
    assert backend.agent.client.chats.create.call_count == 2

@pytest.mark.asyncio
async def test_chat_llm_failure(backend):
    """Test graceful handling of LLM failures."""
    user_name = "error_user"
    
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = None
    mock_db.add = MagicMock()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    # Simulate LLM raising an exception
    backend.agent.process_chat_turn.side_effect = Exception("API Error")
    
    mock_chat_obj = MagicMock()
    backend.agent.client.chats.create.return_value = mock_chat_obj

    with patch("src.services.chat_service.AsyncSessionLocal", return_value=mock_db):
        response = await backend.chat(user_name, "Hi")
    
    # Should return the friendly error message defined in chat_service.py
    assert "something is wrong with my network" in response
