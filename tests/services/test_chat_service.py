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
    with patch("src.services.chat_service.load_config") as mock_load_config, \
         patch("src.services.chat_service.GenericGemini", return_value=mock_agent), \
         patch("src.services.chat_service.genai.Client", return_value=mock_genai_client), \
         patch("src.services.chat_service.GeminiToolRegistry") as mock_registry_cls:
        
        mock_config = MagicMock()
        mock_config.model = "test-model"
        mock_config.system_instruction = "sys"
        mock_config.temperature = 0.5
        mock_config.max_output_tokens = 100
        mock_load_config.return_value = mock_config
        
        # Mock the registry instance
        mock_registry_instance = MagicMock()
        mock_registry_cls.return_value = mock_registry_instance
        
        backend = SmartGeminiBackend("fake_key")
        
        # Attach mocks to backend for verification in tests if needed
        backend.mock_registry = mock_registry_instance
        
        return backend

# --- Tests ---

def test_init_registers_tools(backend):
    """Test that the backend initializes and registers tools."""
    # Verify that register was called on the registry
    # We need to import the tool to check if it was passed
    from src.tools.example_tool import request_weather_tool
    backend.mock_registry.register.assert_called_with(request_weather_tool)

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
    
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = None
    mock_db.add = MagicMock()
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    # Mock Agent response
    # chat returns (response_text, history)
    expected_history = [{"role": "user", "parts": [{"text": "Hello"}]}, {"role": "model", "parts": [{"text": "Hi there"}]}]
    backend.agent.chat.return_value = ("Hi there", expected_history)
    
    # Mock Chat object history
    mock_chat_obj = MagicMock()
    mock_chat_obj.get_history.return_value = []
    backend.agent.client.chats.create.return_value = mock_chat_obj

    with patch("src.services.chat_service.AsyncSessionLocal", return_value=mock_db):
        response = await backend.chat(user_name, prompt)
    
    assert response == "Hi there"
    
    # Verify DB interaction
    mock_db.add.assert_called_once() 
    # Check what was added
    added_session = mock_db.add.call_args[0][0]
    assert isinstance(added_session, ChatSession)
    assert added_session.user_name == user_name
    assert json.loads(added_session.history_json) == expected_history
    
    mock_db.commit.assert_called_once()

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
        user_name=user_name,
        history_json=json.dumps(existing_history),
        last_active=time.time()
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_session
    mock_db.execute.return_value = mock_result
    
    new_history = existing_history + [{"role": "user", "parts": [{"text": "How are you?"}]}, {"role": "model", "parts": [{"text": "I am good"}]}]
    backend.agent.chat.return_value = ("I am good", new_history)
    
    mock_chat_obj = MagicMock()
    mock_chat_obj.get_history.return_value = existing_history
    backend.agent.client.chats.create.return_value = mock_chat_obj

    with patch("src.services.chat_service.AsyncSessionLocal", return_value=mock_db):
        response = await backend.chat(user_name, prompt)
    
    assert response == "I am good"
    
    # Verify history was loaded
    backend.agent.client.chats.create.assert_called_once()
    call_kwargs = backend.agent.client.chats.create.call_args.kwargs
    assert call_kwargs['history'] == existing_history
    
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
        user_name=user_name,
        history_json='[{"role": "user", "parts": [{"text": "old stuff"}]}]',
        last_active=time.time() - (TIMEOUT_SECONDS + 100)
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_session
    mock_db.execute.return_value = mock_result
    
    new_history = [{"role": "user", "parts": [{"text": "New topic"}]}, {"role": "model", "parts": [{"text": "Sure"}]}]
    backend.agent.chat.return_value = ("Sure", new_history)
    
    mock_chat_obj = MagicMock()
    mock_chat_obj.get_history.return_value = []
    backend.agent.client.chats.create.return_value = mock_chat_obj

    with patch("src.services.chat_service.AsyncSessionLocal", return_value=mock_db):
        response = await backend.chat(user_name, prompt)
    
    assert response == "Sure"
    
    # Verify history was NOT loaded (empty list passed)
    backend.agent.client.chats.create.assert_called_once()
    call_kwargs = backend.agent.client.chats.create.call_args.kwargs
    assert call_kwargs['history'] == []
    
    # Verify DB update (should overwrite history)
    assert json.loads(existing_session.history_json) == new_history

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
    backend.agent.chat.side_effect = lambda h, p: (f"Echo: {p}", [])

    results = await asyncio.gather(
        chat_simulation(user1, "Hello from 1"),
        chat_simulation(user2, "Hello from 2")
    )
    
    assert results[0] == "Echo: Hello from 1"
    assert results[1] == "Echo: Hello from 2"
    
    assert backend.agent.client.chats.create.call_count == 2

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
    
    mock_chat_obj = MagicMock()
    mock_chat_obj.get_history.return_value = []
    backend.agent.client.chats.create.return_value = mock_chat_obj

    with patch("src.services.chat_service.AsyncSessionLocal", return_value=mock_db):
        response = await backend.chat(user_name, "Hi")
    
    assert "something is wrong with my network" in response

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
