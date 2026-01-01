import pytest
from unittest.mock import MagicMock, AsyncMock
from google.genai import types
from src.core.agent import GenericAgent
from src.core.tools import AgentToolRegistry

@pytest.fixture
def mock_client():
    client = MagicMock()
    client.chats.create = MagicMock()
    client.models.generate_content = MagicMock()
    return client

@pytest.fixture
def mock_registry():
    registry = MagicMock(spec=AgentToolRegistry)
    registry.tool_object = None
    registry.implementations = {}
    return registry

@pytest.fixture
def agent(mock_client, mock_registry):
    return GenericAgent(
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
    agent.create_chat()
    mock_client.chats.create.assert_called_once()
    
    call_args = mock_client.chats.create.call_args
    assert call_args.kwargs['model'] == "gemini-pro"
    assert call_args.kwargs['config'] == agent.config
    assert call_args.kwargs['history'] is None

@pytest.mark.asyncio
async def test_ask(agent, mock_client):
    # Mock create_chat to return a mock chat object
    mock_chat = MagicMock()
    mock_client.chats.create.return_value = mock_chat
    
    # Mock process_chat_turn behavior (since we are testing ask, we can mock the internal call or the chat behavior)
    # However, since ask calls process_chat_turn, and process_chat_turn is async, we need to handle that.
    # But wait, ask calls process_chat_turn on the agent instance. 
    # Let's mock the chat.send_message to return a simple response so process_chat_turn works.
    
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
async def test_process_chat_turn_simple_response(agent):
    mock_chat = MagicMock()
    mock_response = MagicMock()
    mock_part = MagicMock()
    mock_part.function_call = None
    mock_part.text = "Hello user"
    mock_response.parts = [mock_part]
    
    mock_chat.send_message.return_value = mock_response
    
    response = await agent.process_chat_turn(mock_chat, "Hi")
    
    assert response == "Hello user"
    mock_chat.send_message.assert_called_once_with("Hi")

@pytest.mark.asyncio
async def test_process_chat_turn_with_function_call(agent, mock_registry):
    # Setup function call
    mock_chat = MagicMock()
    
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
    
    response = await agent.process_chat_turn(mock_chat, "Do something")
    
    assert response == "Final answer"
    assert mock_chat.send_message.call_count == 2
    mock_tool.assert_called_once_with(arg="value")

@pytest.mark.asyncio
async def test_process_chat_turn_chained_function_calls(agent, mock_registry):
    """
    Tests a scenario where the LLM calls Tool A, gets a result, 
    then calls Tool B, gets a result, and finally answers.
    """
    mock_chat = MagicMock()
    
    # 1. LLM calls get_location
    resp1 = MagicMock()
    part1 = MagicMock()
    part1.function_call.name = "get_location"
    part1.function_call.args = {}
    part1.text = None
    resp1.parts = [part1]
    
    # 2. LLM calls get_weather(location="Berlin")
    resp2 = MagicMock()
    part2 = MagicMock()
    part2.function_call.name = "get_weather"
    part2.function_call.args = {"city": "Berlin"}
    part2.text = None
    resp2.parts = [part2]
    
    # 3. LLM gives final answer
    resp3 = MagicMock()
    part3 = MagicMock()
    part3.function_call = None
    part3.text = "It is sunny in Berlin."
    resp3.parts = [part3]
    
    mock_chat.send_message.side_effect = [resp1, resp2, resp3]
    
    # Setup tools
    mock_registry.implementations = {
        "get_location": MagicMock(return_value="Berlin"),
        "get_weather": MagicMock(return_value="Sunny")
    }
    
    response = await agent.process_chat_turn(mock_chat, "What's the weather like where I am?")
    
    assert response == "It is sunny in Berlin."
    assert mock_chat.send_message.call_count == 3
    
    # Verify tool calls
    mock_registry.implementations["get_location"].assert_called_once()
    mock_registry.implementations["get_weather"].assert_called_once_with(city="Berlin")

@pytest.mark.asyncio
async def test_process_chat_turn_tool_error(agent, mock_registry):
    """
    Tests that if a tool raises an exception, the error is caught 
    and sent back to the LLM as a string, allowing the conversation to continue.
    """
    mock_chat = MagicMock()
    
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
    
    response = await agent.process_chat_turn(mock_chat, "Use the broken tool")
    
    assert response == "Sorry, I could not use that tool."
    
    # Verify that the error message was sent back to the chat
    # The second call to send_message should contain the error string
    call_args_list = mock_chat.send_message.call_args_list
    assert len(call_args_list) == 2
    
    # Check the argument of the second call (index 1)
    # It should be a Part with FunctionResponse containing the error message
    second_call_arg = call_args_list[1][0][0] # args[0] is the Part object
    assert isinstance(second_call_arg, types.Part)
    assert second_call_arg.function_response.name == "broken_tool"
    
    # The implementation in agent.py now returns "error" key instead of "result"
    assert "Something went wrong" in str(second_call_arg.function_response.response["error"])

@pytest.mark.asyncio
async def test_process_chat_turn_max_loops_exceeded(agent, mock_registry):
    """
    Tests that the agent stops looping if the model keeps requesting function calls
    beyond the _MAX_LOOPS limit.
    """
    mock_chat = MagicMock()
    
    # Create a response that ALWAYS requests a function call
    loop_response = MagicMock()
    part = MagicMock()
    part.function_call.name = "infinite_loop_tool"
    part.function_call.args = {}
    part.text = None
    loop_response.parts = [part]
    
    # The agent should call send_message up to _MAX_LOOPS times.
    # We need to provide enough side effects.
    # 1 initial call + 5 loop calls = 6 calls total.
    mock_chat.send_message.return_value = loop_response
    
    mock_registry.implementations = {"infinite_loop_tool": MagicMock(return_value="ok")}
    
    # We expect the loop to break and return an empty string (or whatever the last text part was, which is None here)
    response = await agent.process_chat_turn(mock_chat, "Start loop")
    
    # It should return empty string because the last response had no text, only function call
    assert response == ""
    
    # Verify it didn't loop forever. 
    # Initial call (1) + 5 loop iterations = 6 calls to send_message
    # Actually, inside the loop:
    # 1. response = chat.send_message(user_prompt) (Initial)
    # Loop 1:
    #   tool execution
    #   response = chat.send_message(function_response)
    # ...
    # Loop 5:
    #   tool execution
    #   response = chat.send_message(function_response)
    # Loop 6 (start):
    #   part = response.parts[0] (which is the result of the 5th call)
    #   if it has function call, we enter loop... wait, range(_MAX_LOOPS) is 0..4
    
    # So we have 5 iterations.
    # 1 initial call.
    # 5 calls inside the loop sending function results.
    # Total 6 calls.
    assert mock_chat.send_message.call_count == 6
