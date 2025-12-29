from google import genai
from google.genai import types, Client
from google.genai.chats import Chats
from pydantic import BaseModel

# Import only the simple, static configurations from settings
from src.config.settings import GEMINI_API_KEY
# Import the config loader directly
from src.config.config_loader import load_config
from src.llm.registry import tool_registry

# --- Global Instances ---
# Load the LLM configuration here, breaking the circular import.
LLM_CONFIG = load_config()

_gemini_api_key = GEMINI_API_KEY
# The client gets the API key from the environment variable `GEMINI_API_KEY`.
_client = genai.Client(api_key=_gemini_api_key)

class HomeAgent:
    def __init__(self, client: genai.Client):
        self.model: str = LLM_CONFIG.model
        self.config: types.GenerateContentConfig = LLM_CONFIG.generate_content_config
        self.client: genai.Client = client

    def get_chat(self):
        try:
            return self.client.chats.create(
                    model=self.model,
                    config=self.config,
                    history=None
                    )

        except Exception as e:
            print(f"Failed to create chat!\n{e}")
            return False

    def ask(self, prompt: str):
        try:
            return self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=self.config
            ).text
        except Exception as e:
            print(f"Failed to answer!\n{e}")
            return False

async def process_chat_turn(chat: types.UserContent, user_prompt: str) -> str:
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
        # It has a safety break after 5 iterations to prevent infinite loops.
        for _ in range(5):  # Max 5 sequential function calls
            part = response.parts[0]
            if not part.function_call:
                # If there's no function call, we have our final text response.
                break

            # --- Execute the function call ---
            function_call = part.function_call
            function_name = function_call.name
            print(f"LLM wants to call function: {function_name}({dict(function_call.args)})")

            try:
                # 1. Look up the implementation and call it with the provided arguments
                tool_function = tool_registry.implementations[function_name]
                function_result = tool_function(**dict(function_call.args))

                # 2. Send the function's result back to the model.
                response = chat.send_message(
                    types.Part(function_response=types.FunctionResponse(
                        name=function_name,
                        response={"result": function_result},
                    ))
                )

            except Exception as e:
                print(f"Error during function call '{function_name}': {e}")
                # Return the error to the user to avoid getting stuck
                return f"Error executing tool {function_name}: {e}"

        # After the loop, return the final text response from the LLM.
        return response.parts[0].text if response.parts and response.parts[0].text else ""

    except Exception as e:
        print(f"An error occurred while processing chat turn: {e}")
        # Re-raise the exception to be handled by the API layer
        raise
            