from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy import String, Float, Text, Integer, ForeignKey

class Base(AsyncAttrs, DeclarativeBase):
    """
    Base class for all database models.

    Inherits from AsyncAttrs to support asyncio features and DeclarativeBase for
    SQLAlchemy's declarative syntax.
    """
    pass

class User(Base):
    """
    Represents a user in the system.

    Attributes:
        name (str): The unique name of the user. Serves as the primary key.
        sessions (list[ChatSession]): A list of chat sessions associated with the user.
    """
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    sessions: Mapped[list["ChatSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class ChatSession(Base):
    """
    Represents a chat session associated with a user.

    Attributes:
        session_id (str): The unique identifier for the chat session.
        user_name (str): The name of the user who owns this session.
        history_json (str): JSON string representation of the chat history.
        last_active (float): Timestamp of the last activity in the session.
        token_count (int): Total number of tokens used in the session.
        version (int): Version number for optimistic locking.
        user (User): The user object associated with this session.
    """
    __tablename__ = "chat_sessions"

    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_name: Mapped[str] = mapped_column(ForeignKey("users.name"), index=True)
    history_json: Mapped[str] = mapped_column(Text, default="[]")
    last_active: Mapped[float] = mapped_column(Float)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)

    user: Mapped["User"] = relationship(back_populates="sessions")

    __mapper_args__ = {"version_id_col": version}
