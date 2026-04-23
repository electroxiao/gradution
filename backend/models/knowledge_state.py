from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.session import Base


class UserKnowledgeState(Base):
    __tablename__ = "user_knowledge_states"
    __table_args__ = (
        UniqueConstraint("user_id", "node_id", name="uq_user_node_state"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    node_id: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(32), default="weak")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="knowledge_states")


class UserConceptMastery(Base):
    __tablename__ = "user_concept_mastery"
    __table_args__ = (
        UniqueConstraint("student_id", "knowledge_node_id", name="uq_student_knowledge_mastery"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    knowledge_node_id: Mapped[int] = mapped_column(ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), index=True)
    mastery_score: Mapped[int] = mapped_column(Integer, default=50, server_default="50")
    positive_evidence_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    negative_evidence_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(32), default="partial", server_default="partial")
    last_source_submission_id: Mapped[int | None] = mapped_column(
        ForeignKey("assignment_submissions.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_evaluated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", foreign_keys=[student_id])
    knowledge_node = relationship("KnowledgeNode")
