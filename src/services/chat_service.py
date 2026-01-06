import time
import json
import asyncio

from google.genai.types import Content, ContentDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from fastapi import HTTPException
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

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
        if len(prompt) > 1000:
            raise HTTPException(status_code=400, detail="Prompt too long.")
        logger.debug(f"generate_content: {prompt}")
        history = []
        response = await self.agent.chat(history=history, user_prompt=prompt)
        return response.last_response.text

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(0.5),
        retry=retry_if_exception_type((IntegrityError, StaleDataError)),
        reraise=True
    )
    async def chat(self, user_name: str,
                   prompt: str,
                   session_id: str = None) -> tuple[str, str]:
        """
        Handles a single chat turn for a given user.
        Checks if the previous session is expired (older than TIMEOUT_SECONDS).

        Returns a tuple of (response_text, session_id).
        """
        logger.debug(f"chat: {user_name=}, {session_id=}, prompt={prompt[:50]}...")

        # --- Phase 1: Load Context (DB) ---
        history: list[Content | ContentDict] = []
        db_session_data = None
        
        async with AsyncSessionLocal() as db:
            db_service = ChatSessionDBService(db)
            try:
                # 1. LOAD SESSION FROM SESSION_ID OR USER_NAME
                # Use a distinct variable name to avoid confusion with Phase 3
                initial_db_session = await db_service.get_session(session_id, user_name)
                
                current_time: float = time.time()

                # 2. CHECK EXPIRATION & LOAD HISTORY
                if initial_db_session:
                    is_expired = (current_time - initial_db_session.last_active) > TIMEOUT_SECONDS
                    
                    if is_expired:
                        logger.info(f"Session {initial_db_session.session_id} for {user_name} has expired.")
                        if session_id is None:
                            # If user didn't request this specific session, drop it and start fresh.
                            logger.info(">> Starting a new session because the previous one expired.")
                            initial_db_session = None
                        else:
                            # If user requested this session specifically, we keep the ID but reset state.
                            logger.info("Resetting expired session state (keeping ID).")
                            # We mark it for reset, but don't write to DB yet.
                            db_session_data = {"session_id": initial_db_session.session_id, "token_count": 0, "reset": True}
                    else:
                        # Session is active, load history
                        history = self._load_history(initial_db_session, user_name)
                        db_session_data = {
                            "session_id": initial_db_session.session_id,
                            "token_count": initial_db_session.token_count,
                            "reset": False
                        }

                # 3. CHECK TOKEN LIMIT
                if initial_db_session and not (db_session_data and db_session_data.get("reset")):
                    self._check_token_limit(initial_db_session)

            except Exception as e:
                logger.error(f"Error loading session for {user_name}: {e}")
                raise

        # --- Phase 2: Process (LLM Call) - No DB Connection ---
        try:
            chat_response: GeminiChatResponse = await self.agent.chat(history, prompt)
        except Exception as e:
            logger.exception(f"LLM Call failed for {user_name}: {e}")
            raise HTTPException(status_code=503, detail="The AI service is currently unavailable.")

        # --- Phase 3: Save State (DB) ---
        async with AsyncSessionLocal() as db:
            db_service = ChatSessionDBService(db)
            try:
                # Serialize the NEW, complete history returned by the agent
                new_history_data: list[dict] = self._serialize_history(chat_response.history)
                if not new_history_data and chat_response.history:
                    logger.warning("Serialized history is empty despite chat_history not being empty!")

                _gemini_tokens: GeminiTokens = chat_response.last_response.tokens
                token_usage = _gemini_tokens.total_token_count if _gemini_tokens else 0

                target_session_id = db_session_data["session_id"] if db_session_data else session_id
                
                # Explicitly initialize final_db_session to ensure we don't use stale objects
                final_db_session = None

                if target_session_id:
                     final_db_session = await db_service.get_session(target_session_id, user_name)

                if not final_db_session:
                    # Create new session if none existed or previous was dropped
                    final_db_session = await db_service.create_session(user_name, target_session_id)

                # Determine if we need to reset the token count (start fresh) or just add to it
                should_reset = db_session_data and db_session_data.get("reset")

                await db_service.update_session(
                    session=final_db_session, 
                    history_data=new_history_data, 
                    token_usage=token_usage,
                    reset_token_count=should_reset
                )
                await db_service.commit()
                
                return chat_response.last_response.text, str(final_db_session.session_id)

            except (IntegrityError, StaleDataError) as e:
                await db_service.rollback()
                logger.warning(f"Race condition detected for user {user_name}. Retrying via tenacity...")
                raise e # Tenacity will catch this and retry
            except Exception as e:
                logger.error(f"Error saving session for {user_name}: {e}")
                raise

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
        """
        To prevent big chats, we will make sure, that the history of a chat can not be larger
        than env_settings.MAX_HISTORY_LENGTH.

        Ensures that the sliced history starts with a 'user' role to avoid API errors.
        """
        max_len = env_settings.MAX_HISTORY_LENGTH
        if len(history) <= max_len:
            return history

        # Slice the last max_len elements
        sliced_history = history[-max_len:]
        
        # Ensure the first element is from the user
        # If the first element is 'model' or 'function', we skip until we find 'user'
        # This is a simple heuristic. A more robust one would check for valid turn sequences.
        while sliced_history:
            first_item = sliced_history[0]
            role = None

            if isinstance(first_item, dict):
                role = first_item.get("role")
            elif hasattr(first_item, "role"):
                role = first_item.role
            
            if role == "user":
                break
            
            # Remove invalid start
            sliced_history.pop(0)
            
        if len(sliced_history) < len(history[-max_len:]):
             logger.warning(f"History was trimmed to ensure valid start. New length: {len(sliced_history)}")

        return sliced_history
    
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
