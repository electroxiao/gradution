from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.session import Base


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    teacher = relationship("User", foreign_keys=[teacher_id])
    questions = relationship(
        "AssignmentQuestion",
        back_populates="assignment",
        cascade="all, delete-orphan",
        order_by="AssignmentQuestion.sort_order",
    )
    assignees = relationship(
        "AssignmentAssignee",
        back_populates="assignment",
        cascade="all, delete-orphan",
    )


class AssignmentQuestion(Base):
    __tablename__ = "assignment_questions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    prompt: Mapped[str] = mapped_column(Text)
    starter_code: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(32), default="java")
    grading_mode: Mapped[str] = mapped_column(String(32), default="testcase", server_default="testcase")
    ai_grading_rubric: Mapped[str] = mapped_column(Text, default="")
    ai_grading_focus_json: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    ai_grading_pass_threshold: Mapped[int] = mapped_column(Integer, default=85, server_default="85")
    ai_grading_confidence_threshold: Mapped[float] = mapped_column(default=0.85, server_default="0.85")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    assignment = relationship("Assignment", back_populates="questions")
    test_cases = relationship(
        "AssignmentTestCase",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="AssignmentTestCase.sort_order",
    )
    submissions = relationship(
        "AssignmentSubmission",
        back_populates="question",
        cascade="all, delete-orphan",
    )


class AssignmentTestCase(Base):
    __tablename__ = "assignment_test_cases"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("assignment_questions.id", ondelete="CASCADE"), index=True)
    input_data: Mapped[str] = mapped_column(Text, default="")
    expected_output: Mapped[str] = mapped_column(Text, default="")
    is_sample: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    question = relationship("AssignmentQuestion", back_populates="test_cases")


class AssignmentAssignee(Base):
    __tablename__ = "assignment_assignees"
    __table_args__ = (
        UniqueConstraint("assignment_id", "student_id", name="uq_assignment_student"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    assignment = relationship("Assignment", back_populates="assignees")
    student = relationship("User", foreign_keys=[student_id])


class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("assignment_questions.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="submitted", index=True)
    results_json: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    ai_context_json: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    ai_review_json: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    final_decision_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    teacher_review_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    teacher_review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    assignment = relationship("Assignment")
    question = relationship("AssignmentQuestion", back_populates="submissions")
    student = relationship("User", foreign_keys=[student_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
