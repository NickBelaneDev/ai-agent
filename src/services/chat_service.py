import asyncio
import time
import json
from sqlalchemy import select

from src.db.connection import AsyncSessionLocal
from src.db.models import ChatSession

from google import genai

from src.config.settings import env_settings, TIMEOUT_SECONDS
from src.llm.client import HomeAgent, process_chat_turn
from src.config.logging_config import logger

class SmartGeminiBackend:
    """
    A backend service to host and manage a collection of chat sessions.
    It monitors chats, decides when to start a new one, and when to forget an old one.
    Chat sessions are persisted in the database.
    """
    def __init__(self, api_key: str):
        self._raw_client = genai.Client(api_key=api_key)
        self.agent = HomeAgent(self._raw_client)

    async def generate_content(self, prompt: str) -> str:
        logger.debug(f"generate_content: {prompt}")
        return self.agent.ask(prompt)

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
            # Note: The SDK usually accepts a list of dicts for history if structure matches.
            chat_object = self.agent.client.chats.create(
                model=self.agent.model,
                config=self.agent.config,
                history=history
            )
            
            # Process the turn (sends message to LLM)
            response_text = await process_chat_turn(chat_object, prompt)
            
            # Retrieve history using the correct method (get_history instead of .history attribute)
            history_list = []
            if hasattr(chat_object, "get_history"):
                history_list = chat_object.get_history()
            else:
                # Fallback just in case, though inspection showed get_history exists
                logger.warning("chat_object.get_history() not found. Trying to find alternative...")
                if hasattr(chat_object, "history"):
                    history_list = chat_object.history

            new_history_data = self._serialize_history(history_list)
            
            if not new_history_data:
                logger.warning("Serialized history is empty! DB will be empty.")

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
            # Prüfen, ob das Objekt eine 'model_dump' Methode hat (Pydantic v2)
            if hasattr(item, "model_dump"):
                serialized.append(item.model_dump(mode="json"))
            elif hasattr(item, "to_dict"):
                serialized.append(item.to_dict())
            elif isinstance(item, dict):
                serialized.append(item)
            else:
                # Fallback: Wenn wir nicht sicher sind, was es ist, ignorieren wir es lieber
                # um Crashs zu vermeiden, oder loggen eine Warnung.
                logger.warning(f"Konnte History-Item nicht serialisieren: {type(item)}")
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