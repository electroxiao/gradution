from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.session import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    knowledge_events = relationship("ChatKnowledgeEvent", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    keywords_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    facts_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    reasoning_trace_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    retrieval_trace_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")
    consultation_events_as_user = relationship(
        "ChatKnowledgeEvent",
        foreign_keys="ChatKnowledgeEvent.user_message_id",
        back_populates="user_message",
        cascade="all, delete-orphan",
    )
    consultation_events_as_assistant = relationship(
        "ChatKnowledgeEvent",
        foreign_keys="ChatKnowledgeEvent.assistant_message_id",
        back_populates="assistant_message",
        cascade="all, delete-orphan",
    )


class ChatKnowledgeEvent(Base):
    __tablename__ = "chat_knowledge_events"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "session_id",
            "user_message_id",
            "assistant_message_id",
            "knowledge_node_id",
            name="uq_chat_knowledge_event_turn_node",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    user_message_id: Mapped[int] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True)
    assistant_message_id: Mapped[int] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True)
    knowledge_node_id: Mapped[int] = mapped_column(ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session = relationship("ChatSession", back_populates="knowledge_events")
    user_message = relationship(
        "ChatMessage",
        foreign_keys=[user_message_id],
        back_populates="consultation_events_as_user",
    )
    assistant_message = relationship(
        "ChatMessage",
        foreign_keys=[assistant_message_id],
        back_populates="consultation_events_as_assistant",
    )
    knowledge_node = relationship("KnowledgeNode")
