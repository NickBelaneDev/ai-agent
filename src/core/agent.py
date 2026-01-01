from google import genai
from google.genai import types

from src.core.tools import AgentToolRegistry
from src.config.logging_config import logger


class GenericAgent:
    """The HomeAgent is the basic model, that we have configured with our '"""
    def __init__(self,
                 client: genai.Client,
                 model_name: str,
                 sys_instruction: str,
                 registry: AgentToolRegistry,
                 temp:float = 1.0,
                 max_tokens: int = 100
                 ):

        self.model: str = model_name
        self.registry: AgentToolRegistry = registry or AgentToolRegistry()
        
        # Only include tools if there are any registered
        tool_obj = self.registry.tool_object
        tools_config = [tool_obj] if tool_obj else None

        self.config: types.GenerateContentConfig = types.GenerateContentConfig(
            system_instruction=sys_instruction,
            temperature=temp,
            max_output_tokens=max_tokens,
            tools=tools_config
        )

        self.client: genai.Client = client

    def create_chat(self, model: str = None):
        """Create a new Chat with gemini."""
        if not model:
            model = self.model

        try:
            return self.client.chats.create(
                    model=model,
                    config=self.config,
                    history=None
                    )

        except Exception as e:
            logger.error(f"Failed to create chat!\n{e}")
            return False

    async def ask(self, prompt: str, model: str = None):
        """Generates content from a given prompt. Handles function calls via a temporary chat."""
        if not model:
            model = self.model

        try:
            # We use a temporary chat session to handle the tool execution loop (Model -> Tool -> Model)
            chat = self.create_chat(model=model)
            return await self.process_chat_turn(chat, prompt)
        except Exception as e:
            logger.error(f"Failed to answer!\n{e}")
            return False

    async def process_chat_turn(self, chat: types.UserContent, user_prompt: str) -> str:
        """
        Processes a single turn of a chat, handling user input and any subsequent
        function calls requested by the model.

        Args:
            chat: The active chat session object.
            user_prompt: The user's message.

        Returns:
            The final text response from the LLM after all processing is complete.
        """
        try:
            response = chat.send_message(user_prompt)

            # This loop continues as long as the model requests function calls.
            _MAX_LOOPS: int = 5
            for _ in range(_MAX_LOOPS):
                # Search for a function call in any part of the response
                target_part = next((p for p in (response.parts or []) if p.function_call), None)
                if not target_part:
                    # If there's no function call, we have our final text response.
                    break

                # --- Execute the function call ---
                function_call = target_part.function_call
                function_name = function_call.name
                logger.info(f"LLM wants to call function: {function_name}({dict(function_call.args)})")

                try:
                    # 1. Look up the implementation and call it with the provided arguments
                    tool_function = self.registry.implementations[function_name]
                    function_result = tool_function(**dict(function_call.args))

                    # 2. Send the function's result back to the model.
                    response = chat.send_message(
                        types.Part(function_response=types.FunctionResponse(
                            name=function_name,
                            response={"result": function_result},
                        ))
                    )

                except Exception as e:
                    logger.exception(f"Error during function call '{function_name}': {e}")
                    # Instead of returning the error string directly to the user,
                    # we send it back to the LLM so it can decide what to do (e.g., apologize).
                    response = chat.send_message(
                        types.Part(function_response=types.FunctionResponse(
                            name=function_name,
                            response={"error": str(e)}, 
                        ))
                    )

            # After the loop, return the final text response from the LLM.
            return "".join([p.text for p in response.parts if p.text]) if response.parts else ""

        except Exception as e:
            logger.error(f"An error occurred while processing chat turn: {e}")
            # Re-raise the exception to be handled by the API layer
            raise