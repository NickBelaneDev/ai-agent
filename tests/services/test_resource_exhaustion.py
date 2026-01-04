import pytest
import asyncio
import json
import time
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import HTTPException

from src.services.chat_service import SmartGeminiBackend
from src.db.models import ChatSession
from src.config.settings import TIMEOUT_SECONDS, env_settings

# --- Fixtures ---

@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.chat = AsyncMock()
    agent.ask = AsyncMock()
    agent.model = "test-model"
    return agent

@pytest.fixture
def backend(mock_agent):
    return SmartGeminiBackend(mock_agent)

# --- Tests ---

@pytest.mark.asyncio
async def test_large_payload_prevention(backend):
    """
    Test that an extremely large chat history payload is truncated or handled
    to prevent database exhaustion.
    """
    user_name = "payload_user"
    prompt = "Update me"
    
    # Create a massive history
    # 10MB string is roughly 10 million characters
    large_text = "a" * (10 * 1024 * 1024) 
    massive_history = [{"role": "user", "parts": [{"text": large_text}]}]
    
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = None
    
    # Mock existing session with massive history
    existing_session = ChatSession(
        session_id="massive-session",
        user_name=user_name,
        history_json=json.dumps(massive_history),
        last_active=time.time()
    )
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_session
    mock_db.execute.return_value = mock_result
    
    # Mock Agent response
    mock_response = MagicMock()
    mock_response.last_response.text = "Processed"
    mock_response.last_response.tokens.total_token_count = 100
    # Return a smaller history to simulate truncation/processing
    mock_response.history = [{"role": "user", "parts": [{"text": "truncated"}]}, {"role": "model", "parts": [{"text": "Processed"}]}]
    
    backend.agent.chat.return_value = mock_response

    with patch("src.services.chat_service.AsyncSessionLocal", return_value=mock_db):
        # We expect the service to handle this without crashing.
        # The _strip_history_length method should be called.
        
        # Spy on _strip_history_length
        with patch.object(SmartGeminiBackend, '_strip_history_length', wraps=SmartGeminiBackend._strip_history_length) as spy_strip:
            response_text, _ = await backend.chat(user_name, prompt)
            
            assert response_text == "Processed"
            spy_strip.assert_called()

@pytest.mark.asyncio
async def test_session_flood_dos(backend):
    """
    Simulate a script creating thousands of new sessions in a short time.
    Verify that the system handles the load (mocked DB) and that we can potentially
    implement rate limiting or connection pool checks here.
    """
    # This test simulates concurrent requests.
    # Since we are mocking the DB, we are testing the asyncio handling and 
    # ensuring no global locks block the requests.
    
    num_requests = 100  # Scaled down for unit test speed
    
    async def single_request(i):
        user_name = f"flood_user_{i}"
        prompt = "Hello"
        
        mock_db = AsyncMock()
        mock_db.__aenter__.return_value = mock_db
        mock_db.__aexit__.return_value = None
        mock_db.add = MagicMock()
        
        # Simulate DB latency
        async def mock_execute(*args, **kwargs):
            await asyncio.sleep(0.001) 
            mock_res = MagicMock()
            mock_res.scalar_one_or_none.return_value = None
            return mock_res
            
        mock_db.execute = AsyncMock(side_effect=mock_execute)
        
        # Mock Agent response
        mock_response = MagicMock()
        mock_response.last_response.text = "Hi"
        mock_response.last_response.tokens.total_token_count = 5
        mock_response.history = []
        
        # We need a new mock for each call to avoid side effects sharing
        local_backend = SmartGeminiBackend(backend.agent)
        local_backend.agent.chat.return_value = mock_response
        
        with patch("src.services.chat_service.AsyncSessionLocal", return_value=mock_db):
            return await local_backend.chat(user_name, prompt)

    # Run concurrently
    start_time = time.time()
    results = await asyncio.gather(*[single_request(i) for i in range(num_requests)])
    end_time = time.time()
    
    assert len(results) == num_requests
    # print(f"Processed {num_requests} requests in {end_time - start_time:.2f} seconds")

@pytest.mark.asyncio
async def test_token_limit_exhaustion(backend):
    """
    Test that a session is blocked if it exceeds the token limit.
    """
    user_name = "token_hog"
    prompt = "More tokens please"
    
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = None
    
    # Mock session that has exceeded the limit
    limit = env_settings.MAX_TOKENS_PER_CHAT_SESSION
    existing_session = ChatSession(
        session_id="hog-session",
        user_name=user_name,
        history_json="[]",
        last_active=time.time(),
        token_count=limit + 100 # Exceeded
    )
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_session
    mock_db.execute.return_value = mock_result
    
    with patch("src.services.chat_service.AsyncSessionLocal", return_value=mock_db):
        with pytest.raises(HTTPException) as excinfo:
            await backend.chat(user_name, prompt)
        
        assert excinfo.value.status_code == 400
        assert "Token limit exceeded" in excinfo.value.detail

@pytest.mark.asyncio
async def test_db_connection_pool_exhaustion_simulation(backend):
    """
    Simulate DB connection failure (pool exhaustion).
    """
    user_name = "db_fail_user"
    prompt = "Hello"
    
    # Mock AsyncSessionLocal to raise an error (simulating pool exhaustion or connection error)
    
    mock_ctx_manager = MagicMock()
    mock_ctx_manager.__aenter__ = AsyncMock(side_effect=Exception("Timeout: pool queue is full"))
    mock_ctx_manager.__aexit__ = AsyncMock()
    
    with patch("src.services.chat_service.AsyncSessionLocal", return_value=mock_ctx_manager):
        with pytest.raises(Exception) as excinfo:
            await backend.chat(user_name, prompt)
        
        assert "Timeout: pool queue is full" in str(excinfo.value)
