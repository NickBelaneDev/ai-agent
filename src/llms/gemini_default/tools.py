from llm_core import ToolDefinition

from ...tools.example_tool import request_weather_tool
from llm_impl import GeminiToolRegistry
from typing import List
from ...config.logging_config import logger


tools = [request_weather_tool]

# Import all tools here and create a singleton of the tool registry.
def create_registry(tool_list: List[ToolDefinition]):
    """Create the tool registry. For now add your tools here, but we will make this more scalable later on."""
    _registry = GeminiToolRegistry()

    if not tool_list:
        return None

    for tool_def in tool_list:
        _registry.register(tool_def)

    logger.info(f"Created tool registry for {__file__}.")
    return _registry

tool_registry = create_registry(tools)