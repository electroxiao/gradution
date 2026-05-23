from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.session import Base


class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    node_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    chapter: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    weak_points = relationship("UserWeakPoint", back_populates="knowledge_node", cascade="all, delete-orphan")


class UserWeakPoint(Base):
    __tablename__ = "user_weak_points"
    __table_args__ = (
        UniqueConstraint("user_id", "knowledge_node_id", name="uq_user_knowledge_node"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    knowledge_node_id: Mapped[int] = mapped_column(ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="unmastered")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="weak_points")
    knowledge_node = relationship("KnowledgeNode", back_populates="weak_points")
