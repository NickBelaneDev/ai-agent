from google.genai import types
from typing import Callable, Dict, List

# Import your tool definitions here.
# As you create more tools in the `src/tools/` directory, you'll import them here.


class AgentToolRegistry:
    """
    A central registry to manage and access all available LLM tools.

    This class holds the function declarations to be sent to the LLM and
    maps function names to their actual Python implementations.
    """

    def __init__(self):
        self.declarations: List[types.FunctionDeclaration] = []
        self.implementations: Dict[str, Callable] = {}

    def register(self, func: Callable, declaration: types.FunctionDeclaration):
        self.declarations.append(declaration)
        self.implementations[declaration.name] = func

    @property
    def tool_object(self) -> types.Tool:
        """Constructs the final Tool object for the Gemini API."""
        return types.Tool(function_declarations=self.declarations) if self.declarations else None
