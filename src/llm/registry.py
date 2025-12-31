from google.genai import types
from typing import Callable, Dict, List

# Import your tool definitions here.
# As you create more tools in the `src/tools/` directory, you'll import them here.


class ToolRegistry:
    """
    A central registry to manage and access all available LLM tools.

    This class holds the function declarations to be sent to the LLM and
    maps function names to their actual Python implementations.
    """

    @property
    def declarations(self) -> List[types.FunctionDeclaration]:
        """Returns a list of all function declarations for the LLM."""
        return [] # Add other declarations here

    @property
    def implementations(self) -> Dict[str, Callable]:
        """
        Returns a dictionary mapping function names to their implementations.
        This is used to execute the function call from the LLM.
        """
        return {
            #"find_recipes": find_recipes,
            # "another_tool_name": another_tool_function,
        }

    @property
    def tool(self) -> types.Tool:
        """Constructs the final Tool object for the Gemini API."""
        return types.Tool(function_declarations=self.declarations)


# Create a single, reusable instance of the registry.
tool_registry = ToolRegistry()
