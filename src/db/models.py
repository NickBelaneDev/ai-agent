from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy import String, Float, Text

class Base(AsyncAttrs, DeclarativeBase):
    pass

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    user_name: Mapped[str] = mapped_column(String, primary_key=True)
    history_json: Mapped[str] = mapped_column(Text, default="[]")
    last_active: Mapped[float] = mapped_column(Float)