import time
import json

from google.genai.types import Content, ContentDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from fastapi import HTTPException

from ..db.connection import AsyncSessionLocal
from ..db.models import ChatSession
from ..db.service import ChatSessionDBService

from llm_impl import GenericGemini, GeminiChatResponse, GeminiTokens

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
        """This methode includes no function calling, it is just for texting! We should update that..."""
        logger.debug(f"generate_content: {prompt}")
        response = await self.agent.ask(prompt)
        return response.text

    async def chat(self, user_name: str,
                   prompt: str,
                   session_id: str = None) -> tuple[str, str]:
        """
        Handles a single chat turn for a given user.
        Checks if the previous session is expired (older than TIMEOUT_SECONDS).
        
        Returns a tuple of (response_text, session_id).
        """
        logger.debug(f"chat: {user_name=}, {session_id=}, prompt={prompt[:50]}...")

        async with AsyncSessionLocal() as db:
            db_service = ChatSessionDBService(db)
            try:
                # 1. LOAD SESSION FROM SESSION_ID OR USER_NAME
                db_session = await db_service.get_session(session_id, user_name)
                
                current_time: float = time.time()
                history: list[Content | ContentDict] = []

                # 2. CHECK EXPIRATION & LOAD HISTORY
                if db_session:
                    is_expired = (current_time - db_session.last_active) > TIMEOUT_SECONDS
                    
                    if is_expired:
                        logger.info(f"Session {db_session.session_id} for {user_name} has expired.")
                        if session_id is None:
                            # If user didn't request this specific session, drop it and start fresh.
                            logger.info(">> Starting a new session because the previous one expired.")
                            db_session = None
                        else:
                            # If user requested this session specifically, we keep the ID but reset state.
                            logger.info("Resetting expired session state (keeping ID).")
                            db_session.token_count = 0
                            # History remains empty []
                    else:
                        # Session is active, load history
                        history = self._load_history(db_session, user_name)
                
                # 3. CHECK TOKEN LIMIT
                if db_session:
                    self._check_token_limit(db_session)
                
                # 4. PROCESS (LLM Call)
                try:
                    chat_response: GeminiChatResponse = await self.agent.chat(history, prompt)
                except Exception as e:
                    logger.exception(f"LLM Call failed for {user_name}: {e}")
                    raise HTTPException(status_code=503, detail="The AI service is currently unavailable.")

                # 5. SAVE (Update DB)
                # Serialize the NEW, complete history returned by the agent
                new_history_data: list[dict] = self._serialize_history(chat_response.history)
                if not new_history_data and chat_response.history:
                    logger.warning("Serialized history is empty despite chat_history not being empty!")

                _gemini_tokens: GeminiTokens = chat_response.last_response.tokens
                token_usage = _gemini_tokens.total_token_count if _gemini_tokens else 0

                if not db_session:
                    # Create new session if none existed or previous was expired/dropped
                    db_session = await db_service.create_session(user_name, session_id)
                
                await db_service.update_session(db_session, new_history_data, token_usage)
                await db_service.commit()
                
                return chat_response.last_response.text, str(db_session.session_id)

            except (IntegrityError, StaleDataError):
                await db_service.rollback()
                logger.warning(f"Race condition detected for user {user_name}. Retrying...")
                # Retry logic
                return await self.chat(user_name, prompt, session_id)

    def _load_history(self,
                      db_session: ChatSession,
                      user_name: str) -> list[Content | ContentDict]:
        """Loads and strips history from the DB session."""
        try:
            history = json.loads(db_session.history_json)
            logger.debug(f"Successfully loaded history for {user_name}. Items: {len(history)}")
            return self._strip_history_length(history)
        except json.JSONDecodeError:
            logger.error(f"Error loading history for {user_name}. Returning empty.")
            return []

    @staticmethod
    def _strip_history_length(history: list[Content | ContentDict]):
        """To prevent big chats, we will make sure, that the history of a chat can not be larger 
        than env_settings.MAX_HISTORY_LENGTH."""
        
        if len(history) >= env_settings.MAX_HISTORY_LENGTH:
            # Safe access to text for logging, assuming structure
            try:
                _text = history[0]['parts'][0]['text']
            except (KeyError, IndexError, TypeError):
                _text = "..."
            logger.warning(f"History of the chat: {_text[:50]} is too long!")
            return history[-env_settings.MAX_HISTORY_LENGTH:]
        return history
    
    @staticmethod
    def _check_token_limit(db_session: ChatSession,
                           max_tokens: int = env_settings.MAX_TOKENS_PER_CHAT_SESSION):
        """Prevent chats from becoming too big, by cutting a max_tokens for a complete chat.
        In case, that the history is shorter than env_settings.MAX_HISTORY_LENGTH, we secure our
        wallet with a maximum tokens per chat."""
        
        # Check if the accumulated tokens exceed the limit
        logger.info(f"Session_ID: {db_session.session_id} has used {db_session.token_count} Tokens out of {max_tokens}.")
        if db_session.token_count and db_session.token_count >= max_tokens:
            raise HTTPException(status_code=400, detail=f"Token limit exceeded. Please start a new or wait {TIMEOUT_SECONDS}s.")

    @staticmethod
    def _serialize_history(history_list: list[Content | ContentDict]) -> list[dict]:
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
                # Fallback: try to construct dict from attributes if possible, or skip
                try:
                    # Basic attempt to capture role and parts if they exist
                    if hasattr(item, "role") and hasattr(item, "parts"):
                        parts_data = []
                        for part in item.parts:
                            if hasattr(part, "text"):
                                parts_data.append({"text": part.text})
                            elif isinstance(part, dict):
                                parts_data.append(part)
                        serialized.append({"role": item.role, "parts": parts_data})
                    else:
                        logger.warning(
                            f"Could not serialize history item of type {type(item)}. "
                            f"It will be skipped."
                        )
                except Exception as e:
                     logger.warning(f"Serialization fallback failed for {type(item)}: {e}")

        return serialized
