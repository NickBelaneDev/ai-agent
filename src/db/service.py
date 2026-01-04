import json
import logging
import time
import uuid
from fastapi import HTTPException

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ChatSession, User

logger = logging.getLogger(__name__)

class ChatSessionDBService:
    """
    Handles database operations for chat sessions and users.
    Separates DB logic from the LLM backend.
    """

    def __init__(self, db: AsyncSession):
        self.db = db


    async def get_or_create_user(self, user_name: str) -> User:
        """
        Ensures a user exists in the database.
        """
        logger.debug(f">> Fetching or creating user: {user_name}")
        result = await self.db.execute(select(User)
                                       .where(User.name == user_name))
        user = result.scalar_one_or_none()
        
        if not user:
            logger.info(f"User {user_name} not found, creating new user.")
            user = User(name=user_name)
            self.db.add(user)
        else:
            logger.debug(f"User {user_name} found.")
        return user


    async def get_session(self, session_id: str = None, user_name: str = None) -> ChatSession | None:
        """
        Retrieves a chat session.
        If session_id is provided, fetches that specific session.
        If only user_name is provided, fetches the most recent session for that user.
        """
        if session_id:
            result = await self.db.execute(select(ChatSession)
                                           .where(ChatSession.session_id == session_id))
            session = result.scalar_one_or_none()

            if session and user_name and (session.user_name != user_name):
                logger.warning(
                    f"Security Alert: User {user_name} tried to access session {session_id}")
                raise HTTPException(status_code=403, detail="Forbidden")
            elif session:
                return session

            raise HTTPException(status_code=404, detail="Session not found")
        
        if user_name:
            logger.debug(f">> Fetching latest session for user: {user_name}")
            statement = (select(ChatSession)
                    .where(ChatSession.user_name == user_name)
                    .order_by(ChatSession.last_active.desc())
                    .limit(1))

            result = await self.db.execute(statement)
            session: ChatSession = result.scalar_one_or_none()

            if session:
                logger.debug(f"Latest session for {user_name} found: {session.session_id}")
            else:
                logger.debug(f"No active session found for user {user_name}.")
            return session
            
        return None


    async def create_session(self, user_name: str, session_id: str = None) -> ChatSession:
        """
        Creates a new chat session for a user.
        """
        logger.info(f">> Creating new session for user: {user_name}")
        # Ensure user exists first
        await self.get_or_create_user(user_name)
        
        new_session_id = session_id if session_id else str(uuid.uuid4())
        new_session = ChatSession(
            session_id=new_session_id,
            user_name=user_name,
            token_count=0,
            last_active=time.time(),
            history_json="[]"
        )
        self.db.add(new_session)
        logger.info(f"Session {new_session_id} created for user {user_name}.")
        return new_session


    async def update_session(self, session: ChatSession, history_data: list[dict], token_usage: int):
        """
        Updates an existing session with new history and token usage.
        """
        logger.debug(f">> Updating session {session.session_id}. Token usage: {token_usage}")
        
        # Update history and last_active on the object (these are absolute updates)
        session.history_json = json.dumps(history_data)
        session.last_active = time.time()
        
        # Use atomic update for token_count to prevent race conditions
        stmt = (
            update(ChatSession)
            .where(ChatSession.session_id == session.session_id)
            .values(token_count=ChatSession.token_count + token_usage)
        )
        await self.db.execute(stmt)
        
        # Note: We don't update session.token_count on the object here because
        # it would require a refresh to get the new DB value.
        # If the caller needs the new value, they should refresh the session.

    async def commit(self):
        logger.debug(">> Committing database transaction.")
        await self.db.commit()

    async def rollback(self):
        logger.warning(">> Rolling back database transaction.")
        await self.db.rollback()
