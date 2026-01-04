import pytest
from unittest.mock import MagicMock, AsyncMock
from google.genai import types
from llm_impl import GenericGemini, GeminiToolRegistry

@pytest.fixture
def mock_client():
    client = MagicMock()
    client.chats.create = MagicMock()
    client.models.generate_content = MagicMock()
    return client

@pytest.fixture
def mock_registry():
    registry = MagicMock(spec=GeminiToolRegistry)
    registry.tool_object = None
    registry.implementations = {}
    return registry

@pytest.fixture
def agent(mock_client, mock_registry):
    return GenericGemini(
        client=mock_client,
        model_name="gemini-pro",
        sys_instruction="You are a helpful assistant.",
        registry=mock_registry
    )

def test_init(agent):
    assert agent.model == "gemini-pro"
    assert agent.config.system_instruction == "You are a helpful assistant."
    assert agent.config.temperature == 1.0
    assert agent.config.max_output_tokens == 100

def test_create_chat(agent, mock_client):
    # GenericGemini doesn't have create_chat exposed directly usually, 
    # but let's assume we want to test the underlying client call if exposed or used.
    # However, GenericGemini.chat() creates the chat object internally or uses one passed to it.
    # Let's test the 'ask' method which is a high level wrapper.
    pass 

@pytest.mark.asyncio
async def test_ask(agent, mock_client):
    # Mock create_chat to return a mock chat object
    mock_chat = MagicMock()
    mock_client.chats.create.return_value = mock_chat
    
    mock_response = MagicMock()
    mock_part = MagicMock()
    mock_part.function_call = None
    mock_part.text = "Response text"
    mock_response.parts = [mock_part]
    mock_chat.send_message.return_value = mock_response

    response = await agent.ask("Hello")
    
    mock_client.chats.create.assert_called_once()
    mock_chat.send_message.assert_called_once_with("Hello")
    assert response == "Response text"

@pytest.mark.asyncio
async def test_chat_simple_response(agent):
    # Test the chat method which takes history
    mock_chat = MagicMock()
    mock_response = MagicMock()
    mock_part = MagicMock()
    mock_part.function_call = None
    mock_part.text = "Hello user"
    mock_response.parts = [mock_part]
    
    # Mock the client creating a chat with history
    agent.client.chats.create.return_value = mock_chat
    mock_chat.send_message.return_value = mock_response
    
    # Mock get_history to return updated history
    mock_chat.get_history.return_value = [{"role": "user", "parts": [{"text": "Hi"}]}, {"role": "model", "parts": [{"text": "Hello user"}]}]

    response_text, history = await agent.chat([], "Hi")
    
    assert response_text == "Hello user"
    assert len(history) == 2
    mock_chat.send_message.assert_called_once_with("Hi")

@pytest.mark.asyncio
async def test_process_chat_turn_with_function_call(agent, mock_registry):
    # We need to mock the internal _process_chat_turn or simulate the chat loop.
    # Since GenericGemini encapsulates this, we test via 'chat' or 'ask'.
    
    mock_chat = MagicMock()
    agent.client.chats.create.return_value = mock_chat
    
    # First response: Function call
    response1 = MagicMock()
    part1 = MagicMock()
    part1.function_call.name = "test_tool"
    part1.function_call.args = {"arg": "value"}
    part1.text = None
    response1.parts = [part1]
    
    # Second response: Final text
    response2 = MagicMock()
    part2 = MagicMock()
    part2.function_call = None
    part2.text = "Final answer"
    response2.parts = [part2]
    
    mock_chat.send_message.side_effect = [response1, response2]
    
    # Setup tool implementation
    mock_tool = MagicMock(return_value="tool_result")
    mock_registry.implementations = {"test_tool": mock_tool}
    
    response_text, _ = await agent.chat([], "Do something")
    
    assert response_text == "Final answer"
    assert mock_chat.send_message.call_count == 2
    mock_tool.assert_called_once_with(arg="value")

@pytest.mark.asyncio
async def test_process_chat_turn_tool_error(agent, mock_registry):
    """
    Tests that if a tool raises an exception, the error is caught 
    and sent back to the LLM.
    """
    mock_chat = MagicMock()
    agent.client.chats.create.return_value = mock_chat
    
    # 1. LLM calls broken_tool
    resp1 = MagicMock()
    part1 = MagicMock()
    part1.function_call.name = "broken_tool"
    part1.function_call.args = {}
    part1.text = None
    resp1.parts = [part1]
    
    # 2. LLM apologizes after seeing the error
    resp2 = MagicMock()
    part2 = MagicMock()
    part2.function_call = None
    part2.text = "Sorry, I could not use that tool."
    resp2.parts = [part2]
    
    mock_chat.send_message.side_effect = [resp1, resp2]
    
    # Setup broken tool
    mock_tool = MagicMock(side_effect=ValueError("Something went wrong"))
    mock_registry.implementations = {"broken_tool": mock_tool}
    
    response_text, _ = await agent.chat([], "Use the broken tool")
    
    assert response_text == "Sorry, I could not use that tool."
    
    # Verify that the error message was sent back to the chat
    call_args_list = mock_chat.send_message.call_args_list
    assert len(call_args_list) == 2
    
    # Check the argument of the second call
    second_call_arg = call_args_list[1][0][0] 
    assert isinstance(second_call_arg, types.Part)
    assert second_call_arg.function_response.name == "broken_tool"
    assert "Something went wrong" in str(second_call_arg.function_response.response["error"])
