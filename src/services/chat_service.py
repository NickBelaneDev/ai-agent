import asyncio
import time
import json
from collections import Counter

from google.genai.types import Content, ContentDict
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from ..db.connection import AsyncSessionLocal, init_db
from ..db.models import ChatSession

from llm_impl import GenericGemini

from ..config.settings import TIMEOUT_SECONDS, env_settings
from ..config.logging_config import logger

class SmartGeminiBackend:
    """
    A backend service to host and manage a collection of chat sessions.
    It monitors chats, decides when to start a new one, and when to forget an old one.
    Chat sessions are persisted in the database.
    """
    def __init__(self, agent: GenericGemini):
        self.agent = agent

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
            try:
                # Attempt to get or create the session
                result = await db.execute(select(ChatSession).where(ChatSession.user_name == user_name))
                db_session = result.scalar_one_or_none()
                current_time = time.time()

                history = self._manage_user_history(db_session, current_time, user_name)

                # Process the turn (sends message to LLM)
                try:
                    response_text, _chat_history = await self.agent.chat(history, prompt) # CHECK HERE
                except Exception as e:
                    logger.error(f"LLM Call failed for {user_name}: {e}")
                    # Raise an HTTPException to inform the client about the failure
                    raise HTTPException(status_code=503, detail="The AI service is currently unavailable.")

                # Write the serialized_history to the database
                new_history_data = self._serialize_history(_chat_history)
                if not new_history_data and _chat_history:
                    logger.warning("Serialized history is empty despite chat_history not being empty!")

                # Instantiate a new ChatSession, if it does not exist yet
                if not db_session:
                    db_session = ChatSession(user_name=user_name)
                    db.add(db_session)

                # Update the chat history
                db_session.history_json = json.dumps(new_history_data)
                db_session.last_active = current_time

                await db.commit()

            except IntegrityError:
                await db.rollback()
                logger.warning(f"Race condition detected for user {user_name}. Retrying...")
                # The session was created by another request, so we fetch it and retry
                result = await db.execute(select(ChatSession).where(ChatSession.user_name == user_name))
                db_session = result.scalar_one()
                
                # And now we can continue with the logic, but we need to re-run the chat
                # This could be refactored to avoid code duplication
                return await self.chat(user_name, prompt)

        # Finally we send the text response
        return response_text


    def _manage_user_history(self, db_session, current_time, user_name) ->  list[Content | ContentDict]:
        """Check if there is an existing history for the user and if it is less the TIMEOUT_SECONDS long, since the latest reply.
        This way we can prevent too long chat histories."""
        if db_session:
            if (current_time - db_session.last_active) > TIMEOUT_SECONDS:
                logger.info(
                    f"Session for {user_name} has expired (inactive > {TIMEOUT_SECONDS}s). Starting a new context.")
                history = []
            else:
                try:
                    history = json.loads(db_session.history_json)
                    logger.info(f"Successfully loaded the history for {user_name}. Items: {len(history)}")
                    history = self._strip_history_length(history)

                except json.JSONDecodeError:
                    logger.error(f"Error at loading history for {user_name}. Start again!")
                    history = []
        else:
            history = []
        return history

    @staticmethod
    def _strip_history_length(history: list):
        """To prevent big chats, we will make sure, that the history of a chat can not be longer than 20 messages."""
        if len(history) >= env_settings.MAX_HISTORY_LENGTH:
            _text = history[0]['parts'][0]['text']
            logger.warning(f"History of the chat: {_text[:50]} is too long!")
            return history[-env_settings.MAX_HISTORY_LENGTH:]
        return history


    @staticmethod
    def _serialize_history(history_list: list) -> list[dict]:
        """
        Serializes a list of chat history items (e.g., Google GenAI Content objects)
        into a list of dictionaries suitable for JSON storage.
        """
        if not history_list:
            return []
            
        serialized = []
        for item in history_list:
            # The google-genai library uses Pydantic models (like Content) for history.
            # .model_dump() is the standard way to serialize them to a dictionary.
            if hasattr(item, "model_dump"):
                serialized.append(item.model_dump(mode="json"))
            # .to_dict() is a common fallback for other object types.
            elif hasattr(item, "to_dict"):
                serialized.append(item.to_dict())
            # When loading from the DB, the history might already be a list of dicts.
            elif isinstance(item, dict):
                serialized.append(item)
            else:
                logger.warning(
                    f"Could not serialize history item of type {type(item)}. "
                    f"It will be skipped, which may lead to an incomplete chat history."
                )

        return serialized


# A small test function for the chat service.
async def main():
    """Main async function to run the chat client for testing."""
    logger.info("Starting SmartGeminiBackend test client...")
    await init_db()
    
    # Import locally to avoid circular imports or path issues during normal execution if not needed
    try:
        from src.llms.gemini_default.gemini import DefaultGeminiLLM
        gemini = SmartGeminiBackend(DefaultGeminiLLM)
    except ImportError:
        logger.warning("Could not import DefaultGeminiLLM. Test client might fail.")
        return

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