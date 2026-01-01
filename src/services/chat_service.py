import asyncio
import time
import json
from sqlalchemy import select
from google import genai

from src.db.connection import AsyncSessionLocal
from src.db.models import ChatSession

from src.core.agent import GenericAgent
from src.core.tools import AgentToolRegistry

from src.config.config_loader import load_config
from src.config.settings import env_settings, TIMEOUT_SECONDS
from src.config.logging_config import logger

from src.tools.example_tool import request_weather, request_weather_declaration


class SmartGeminiBackend:
    """
    A backend service to host and manage a collection of chat sessions.
    It monitors chats, decides when to start a new one, and when to forget an old one.
    Chat sessions are persisted in the database.
    """
    def __init__(self, api_key: str):
        conf = load_config()
        self._raw_client = genai.Client(api_key=api_key)
        registry = AgentToolRegistry()
        registry.register(request_weather, request_weather_declaration)

        self.agent = GenericAgent(
            client=self._raw_client,
            model_name=conf.model,
            sys_instruction=conf.system_instruction,
            temp=conf.temperature,
            max_tokens=conf.max_output_tokens,
            registry=registry
        )

    async def generate_content(self, prompt: str) -> str:
        logger.debug(f"generate_content: {prompt}")
        return await self.agent.ask(prompt)

    async def chat(self, user_name: str, prompt: str) -> str:
        """
        Handles a single chat turn for a given user.
        Checks if the previous session is expired (older than TIMEOUT_SECONDS).
        """
        logger.debug(f"chat: {user_name=}, prompt={prompt[:50]}...")

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(ChatSession).where(ChatSession.user_name == user_name))
            db_session = result.scalar_one_or_none()

            history = []
            current_time = time.time()

            if db_session:
                # Check if the session has expired
                if (current_time - db_session.last_active) > TIMEOUT_SECONDS:
                    logger.info(f"Session for {user_name} has expired (inactive > {TIMEOUT_SECONDS}s). Starting a new context.")
                    history = []
                else:
                    try:
                        history = json.loads(db_session.history_json)
                        logger.info(f"Successfully loaded the history for {user_name}. Items: {len(history)}")
                    except json.JSONDecodeError:
                        logger.error(f"Error at loading history for {user_name}. Start again!")
                        history = []

            # Create chat object with loaded history
            chat_object = self.agent.client.chats.create(
                model=self.agent.model,
                config=self.agent.config,
                history=history
            )
            
            # Process the turn (sends message to LLM)
            try:
                response_text = await self.agent.process_chat_turn(chat_object, prompt)
            except Exception as e:
                logger.error(f"LLM Call failed for {user_name}: {e}")
                # Return a friendly error message instead of crashing
                return "I'm sorry! It seems that something is wrong with my network, at least I am not working right now..."
            
            # Retrieve history using the correct method
            history_list = []
            if hasattr(chat_object, "get_history"):
                history_list = chat_object.get_history()
            elif hasattr(chat_object, "history"):
                history_list = chat_object.history
            else:
                logger.warning("Could not find history on chat object.")

            new_history_data = self._serialize_history(history_list)
            
            if not new_history_data and history_list:
                logger.warning("Serialized history is empty despite history_list not being empty!")

            if not db_session:
                db_session = ChatSession(user_name=user_name)
                db.add(db_session)

            db_session.history_json = json.dumps(new_history_data)
            db_session.last_active = current_time

            await db.commit()

        return response_text

    @staticmethod
    def _serialize_history(history_list) -> list[dict]:
        """
        Helper function: Wraps Google Genai Objects into dicts. 
        """
        if not history_list:
            return []
            
        serialized = []
        for item in history_list:
            # 1. Try standard Pydantic/Dict methods
            if hasattr(item, "model_dump"):
                serialized.append(item.model_dump(mode="json"))
            elif hasattr(item, "to_dict"):
                serialized.append(item.to_dict())
            elif isinstance(item, dict):
                serialized.append(item)
            else:
                # 2. Manual Fallback for Google GenAI Objects
                try:
                    # Extract role
                    role = getattr(item, "role", "unknown")
                    
                    # Extract parts
                    parts_data = []
                    raw_parts = getattr(item, "parts", [])
                    
                    # parts might be a list of Part objects or strings
                    if isinstance(raw_parts, list):
                        for part in raw_parts:
                            if hasattr(part, "text"):
                                parts_data.append({"text": part.text})
                            elif isinstance(part, str):
                                parts_data.append({"text": part})
                            elif isinstance(part, dict):
                                parts_data.append(part)
                            else:
                                parts_data.append({"text": str(part)})
                    
                    serialized.append({
                        "role": role,
                        "parts": parts_data
                    })
                except Exception as e:
                    logger.warning(f"Could not serialize history item: {type(item)} - {e}")

        return serialized


# A small test function for the chat service.
async def main():
    """Main async function to run the chat client for testing."""
    logger.info("Starting SmartGeminiBackend test client...")
    gemini = SmartGeminiBackend(env_settings.GEMINI_API_KEY)

    while True:
        user_prompt = input("\nYou> ")
        if user_prompt.lower() in ["exit", "quit"]:
            break
        response_lines = await gemini.chat("User1", user_prompt)

        # Print each line of the response, simulating how Minecraft would show it.
        # We keep print here as it is the UI for the test client
        if isinstance(response_lines, list):
             for line in response_lines:
                print(f"LLM: {line}")
        else:
             print(f"LLM: {response_lines}")

if __name__ == "__main__":
    # To run an async function from the top level, you use asyncio.run()
    asyncio.run(main())