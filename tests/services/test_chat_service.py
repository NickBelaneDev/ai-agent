import pytest
import asyncio
import json
import time
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy import select

from src.services.chat_service import SmartGeminiBackend
from src.db.models import ChatSession
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
    agent.chat = AsyncMock()
    agent.ask = AsyncMock()
    agent.model = "test-model"
    agent.config = {}
    return agent

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    return session

@pytest.fixture
def backend(mock_genai_client, mock_agent):
    # Since SmartGeminiBackend now takes an agent instance directly,
    # we can just pass the mock_agent.
    backend = SmartGeminiBackend(mock_agent)
    return backend

# --- Tests ---

@pytest.mark.asyncio
async def test_generate_content(backend):
    """Test simple one-off generation."""
    backend.agent.ask.return_value = MagicMock(text="Generated text")
    response = await backend.generate_content("Prompt")
    
    assert response == "Generated text"
    backend.agent.ask.assert_called_once_with("Prompt")

@pytest.mark.asyncio
async def test_chat_new_user(backend):
    """Test chat flow for a new user (no history)."""
    user_name = "new_user"
    prompt = "Hello"
    
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = None
    mock_db.add = MagicMock()
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    # Mock Agent response
    # chat returns GeminiChatResponse
    expected_history = [{"role": "user", "parts": [{"text": "Hello"}]}, {"role": "model", "parts": [{"text": "Hi there"}]}]
    
    mock_response = MagicMock()
    mock_response.last_response.text = "Hi there"
    mock_response.last_response.tokens.total_token_count = 10
    mock_response.history = expected_history
    
    backend.agent.chat.return_value = mock_response
    
    with patch("src.services.chat_service.AsyncSessionLocal", return_value=mock_db):
        response_text, session_id = await backend.chat(user_name, prompt)
    
    assert response_text == "Hi there"
    
    # Verify DB interaction
    # It might be called multiple times if the user is created first, then the session
    assert mock_db.add.call_count >= 1
    
    # Check if session was added
    session_added = False
    for call in mock_db.add.call_args_list:
        if isinstance(call[0][0], ChatSession):
            added_session = call[0][0]
            assert added_session.user_name == user_name
            assert json.loads(added_session.history_json) == expected_history
            session_added = True
            
    assert session_added, "ChatSession was not added to the database"
    
    mock_db.commit.assert_called()

@pytest.mark.asyncio
async def test_chat_existing_user_active(backend):
    """Test chat flow for an existing user with an active session."""
    user_name = "active_user"
    prompt = "How are you?"
    
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = None
    mock_db.add = MagicMock()
    
    existing_history = [{"role": "user", "parts": [{"text": "prev"}]}]
    existing_session = ChatSession(
        session_id="existing-session-id",
        user_name=user_name,
        history_json=json.dumps(existing_history),
        last_active=time.time()
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_session
    mock_db.execute.return_value = mock_result
    
    new_history = existing_history + [{"role": "user", "parts": [{"text": "How are you?"}]}, {"role": "model", "parts": [{"text": "I am good"}]}]
    
    mock_response = MagicMock()
    mock_response.last_response.text = "I am good"
    mock_response.last_response.tokens.total_token_count = 20
    mock_response.history = new_history
    
    backend.agent.chat.return_value = mock_response

    with patch("src.services.chat_service.AsyncSessionLocal", return_value=mock_db):
        response_text, session_id = await backend.chat(user_name, prompt)
    
    assert response_text == "I am good"
    assert session_id == "existing-session-id"
    
    # Verify history was loaded and passed to agent
    backend.agent.chat.assert_called_once()
    call_args = backend.agent.chat.call_args
    assert call_args[0][0] == existing_history # first arg is history
    
    # Verify DB update
    assert json.loads(existing_session.history_json) == new_history
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_chat_existing_user_expired(backend):
    """Test chat flow for an existing user whose session has expired."""
    user_name = "expired_user"
    prompt = "New topic"
    
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = None
    mock_db.add = MagicMock()
    
    existing_session = ChatSession(
        session_id="expired-session-id",
        user_name=user_name,
        history_json='[{"role": "user", "parts": [{"text": "old stuff"}]}]',
        last_active=time.time() - (TIMEOUT_SECONDS + 100)
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_session
    mock_db.execute.return_value = mock_result
    
    new_history = [{"role": "user", "parts": [{"text": "New topic"}]}, {"role": "model", "parts": [{"text": "Sure"}]}]
    
    mock_response = MagicMock()
    mock_response.last_response.text = "Sure"
    mock_response.last_response.tokens.total_token_count = 5
    mock_response.history = new_history
    
    backend.agent.chat.return_value = mock_response

    with patch("src.services.chat_service.AsyncSessionLocal", return_value=mock_db):
        response_text, session_id = await backend.chat(user_name, prompt)
    
    assert response_text == "Sure"
    # Should be a new session ID because the old one expired and we didn't request a specific ID
    assert session_id != "expired-session-id"
    
    # Verify history was NOT loaded (empty list passed)
    backend.agent.chat.assert_called_once()
    call_args = backend.agent.chat.call_args
    assert call_args[0][0] == []
    
    # Verify DB update (should be a new session added)
    mock_db.add.assert_called_once()

@pytest.mark.asyncio
async def test_chat_concurrent_users(backend):
    """Test multiple users chatting concurrently."""
    user1 = "user1"
    user2 = "user2"
    
    async def chat_simulation(user, prompt):
        mock_db = AsyncMock()
        mock_db.__aenter__.return_value = mock_db
        mock_db.__aexit__.return_value = None
        mock_db.add = MagicMock()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with patch("src.services.chat_service.AsyncSessionLocal", return_value=mock_db):
             return await backend.chat(user, prompt)

    # We need backend.agent.chat to return something valid
    def side_effect(history, prompt):
        resp = MagicMock()
        resp.last_response.text = f"Echo: {prompt}"
        resp.last_response.tokens.total_token_count = 1
        resp.history = []
        return resp

    backend.agent.chat.side_effect = side_effect

    results = await asyncio.gather(
        chat_simulation(user1, "Hello from 1"),
        chat_simulation(user2, "Hello from 2")
    )
    
    assert results[0][0] == "Echo: Hello from 1"
    assert results[1][0] == "Echo: Hello from 2"
    
    assert backend.agent.chat.call_count == 2

@pytest.mark.asyncio
async def test_chat_llm_failure(backend):
    """Test graceful handling of LLM failures."""
    user_name = "error_user"
    
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = None

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    backend.agent.chat.side_effect = Exception("API Error")
    
    with patch("src.services.chat_service.AsyncSessionLocal", return_value=mock_db):
        with pytest.raises(Exception) as excinfo:
            await backend.chat(user_name, "Hi")
        assert "The AI service is currently unavailable" in str(excinfo.value.detail)

def test_serialize_history_simple():
    """Test serialization of simple dicts."""
    history = [{"role": "user", "parts": [{"text": "hi"}]}]
    serialized = SmartGeminiBackend._serialize_history(history)
    assert serialized == history

def test_serialize_history_genai_fallback():
    """Test serialization of Google GenAI-like objects."""
    class MockPart:
        def __init__(self, text):
            self.text = text
            
    class MockItem:
        def __init__(self, role, parts):
            self.role = role
            self.parts = parts
            
    history = [MockItem("user", [MockPart("test")])]
    serialized = SmartGeminiBackend._serialize_history(history)
    assert serialized == [{"role": "user", "parts": [{"text": "test"}]}]