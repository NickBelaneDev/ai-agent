import pytest
from unittest.mock import MagicMock
from google.genai import types
from llm_impl import GeminiToolRegistry
from llm_core import ToolDefinition

def test_registry_init():
    registry = GeminiToolRegistry()
    # Check for public properties that should exist
    assert registry.implementations == {}
    assert registry.tool_object is None
    # 'declarations' might be internal or named differently in the new impl.
    # We can check if tool_object is None initially.

def test_register_tool():
    registry = GeminiToolRegistry()
    
    mock_func = MagicMock()
    
    # Create a ToolDefinition
    tool_def = ToolDefinition(
        name="test_tool",
        description="A test tool",
        func=mock_func,
        parameters=types.Schema(type=types.Type.OBJECT, properties={})
    )
    
    registry.register(tool_def)
    
    # Check implementations
    assert "test_tool" in registry.implementations
    assert registry.implementations["test_tool"] == mock_func
    
    # Check that tool_object is updated
    assert registry.tool_object is not None
    assert len(registry.tool_object.function_declarations) == 1
    assert registry.tool_object.function_declarations[0].name == "test_tool"

def test_tool_object_creation():
    registry = GeminiToolRegistry()
    
    mock_func = MagicMock()
    tool_def = ToolDefinition(
        name="test_tool",
        description="A test tool",
        func=mock_func,
        parameters=types.Schema(type=types.Type.OBJECT, properties={})
    )
    
    registry.register(tool_def)
    
    tool_obj = registry.tool_object
    assert isinstance(tool_obj, types.Tool)
    assert len(tool_obj.function_declarations) == 1
    assert tool_obj.function_declarations[0].name == "test_tool"
