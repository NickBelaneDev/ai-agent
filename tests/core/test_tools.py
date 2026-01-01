import pytest
from unittest.mock import MagicMock
from google.genai import types
from src.core.tools import AgentToolRegistry

def test_registry_init():
    registry = AgentToolRegistry()
    assert registry.declarations == []
    assert registry.implementations == {}
    assert registry.tool_object is None

def test_register_tool():
    registry = AgentToolRegistry()
    
    mock_func = MagicMock()
    mock_declaration = MagicMock(spec=types.FunctionDeclaration)
    mock_declaration.name = "test_tool"
    
    registry.register(mock_func, mock_declaration)
    
    assert len(registry.declarations) == 1
    assert registry.declarations[0] == mock_declaration
    assert "test_tool" in registry.implementations
    assert registry.implementations["test_tool"] == mock_func

def test_tool_object_creation():
    registry = AgentToolRegistry()
    
    mock_func = MagicMock()
    mock_declaration = MagicMock(spec=types.FunctionDeclaration)
    mock_declaration.name = "test_tool"
    
    registry.register(mock_func, mock_declaration)
    
    tool_obj = registry.tool_object
    assert isinstance(tool_obj, types.Tool)
    assert tool_obj.function_declarations == [mock_declaration]
