from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.session import Base


class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    node_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    node_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
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
    source_session_id: Mapped[int | None] = mapped_column(ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="weak_points")
    knowledge_node = relationship("KnowledgeNode", back_populates="weak_points")


class PendingNodeProposal(Base):
    __tablename__ = "pending_node_proposals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    desc: Mapped[str] = mapped_column(Text, default="")
    node_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    source_weak_point_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_weak_points.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_chat_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reason: Mapped[str] = mapped_column(Text, default="")
    review_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    suggested_edges = relationship(
        "PendingNodeProposalEdge",
        back_populates="proposal",
        cascade="all, delete-orphan",
    )


class PendingNodeProposalEdge(Base):
    __tablename__ = "pending_node_proposal_edges"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    proposal_id: Mapped[int] = mapped_column(
        ForeignKey("pending_node_proposals.id", ondelete="CASCADE"),
        index=True,
    )
    source_name: Mapped[str] = mapped_column(String(255))
    target_name: Mapped[str] = mapped_column(String(255))
    relation: Mapped[str] = mapped_column(String(64), default="DEPENDS_ON")
    direction: Mapped[str] = mapped_column(String(16), default="out")

    proposal = relationship("PendingNodeProposal", back_populates="suggested_edges")
