from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from src.db.database import Base

class ChatSessionModel(Base):
    __tablename__ = "chat_sessions"

    user_name = Column(String, primary_key=True, index=True)
    history = Column(JSONB, default=list) # Stores the list of messages
    last_active = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())