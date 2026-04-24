from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AssignmentTestCaseInput(BaseModel):
    id: int | None = None
    input_data: str = Field(default="")
    expected_output: str = Field(default="")
    is_sample: bool = True
    sort_order: int = 0


class AssignmentQuestionInput(BaseModel):
    id: int | None = None
    title: str = Field(default="", max_length=255)
    prompt: str = Field(min_length=1)
    starter_code: str = Field(default="")
    knowledge_node_ids: list[int] = Field(default_factory=list)
    language: str = Field(default="java", max_length=32)
    grading_mode: str | None = Field(default=None, max_length=32)
    enable_testcases: bool = True
    ai_review_level: str = Field(default="light", max_length=32)
    ai_grading_rubric: str = Field(default="")
    ai_grading_focus: list[str] = Field(default_factory=list)
    ai_grading_pass_threshold: int = Field(default=85, ge=0, le=100)
    ai_grading_confidence_threshold: float = Field(default=0.85, ge=0, le=1)
    sort_order: int = 0
    test_cases: list[AssignmentTestCaseInput] = Field(default_factory=list)


class AssignmentCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="")
    status: str = Field(default="draft", max_length=32)
    due_at: datetime | None = None
    student_ids: list[int] = Field(default_factory=list)
    questions: list[AssignmentQuestionInput] = Field(default_factory=list)


class AssignmentUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = Field(default=None, max_length=32)
    due_at: datetime | None = None
    student_ids: list[int] | None = None


class AssignmentQuestionsUpdateRequest(BaseModel):
    questions: list[AssignmentQuestionInput] = Field(default_factory=list)


class AssignmentGenerateQuestionRequest(BaseModel):
    requirement: str = Field(min_length=1, max_length=2000)
    knowledge_point: str = Field(default="", max_length=255)


class AssignmentGenerateTestCasesRequest(BaseModel):
    title: str = Field(default="", max_length=255)
    prompt: str = Field(min_length=1, max_length=8000)
    knowledge_point: str = Field(default="", max_length=255)


class AssignmentGenerateFocusRequest(BaseModel):
    title: str = Field(default="", max_length=255)
    prompt: str = Field(min_length=1, max_length=8000)
    ai_grading_rubric: str = Field(default="", max_length=4000)
    ai_review_level: str = Field(default="deep", max_length=32)


class AssignmentSubmitRequest(BaseModel):
    code: str = Field(min_length=1)
    started_at: datetime | None = None


class AssignmentAiHelpRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    code: str = Field(default="")
    last_result: dict[str, Any] | None = None


class AssignmentStudentRef(BaseModel):
    id: int
    username: str

    model_config = {"from_attributes": True}


class AssignmentTestCaseResponse(BaseModel):
    id: int
    input_data: str
    expected_output: str | None = None
    is_sample: bool
    sort_order: int

    model_config = {"from_attributes": True}


class AssignmentQuestionResponse(BaseModel):
    id: int
    title: str
    prompt: str
    starter_code: str = ""
    knowledge_node_ids: list[int] = Field(default_factory=list)
    knowledge_nodes: list[dict[str, Any]] = Field(default_factory=list)
    language: str
    grading_mode: str = "testcase"
    enable_testcases: bool = True
    ai_review_level: str = "light"
    ai_grading_rubric: str = ""
    ai_grading_focus: list[str] = Field(default_factory=list)
    ai_grading_pass_threshold: int = 85
    ai_grading_confidence_threshold: float = 0.85
    sort_order: int
    test_cases: list[AssignmentTestCaseResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class AssignmentSubmissionResponse(BaseModel):
    id: int
    assignment_id: int
    question_id: int
    student_id: int
    code: str
    status: str
    results_json: Any = None
    ai_review_json: Any = None
    decision_source: str | None = None
    manual_review_required: bool = False
    teacher_review_status: str | None = None
    teacher_review_note: str | None = None
    trust_label: str | None = None
    trust_score: float | None = None
    excluded_from_mastery_update: bool = False
    started_at: datetime | None = None
    duration_seconds: int | None = None
    submitted_at: datetime

    model_config = {"from_attributes": True}


class AssignmentSummaryResponse(BaseModel):
    id: int
    title: str
    description: str
    status: str
    due_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    question_count: int = 0
    assignee_count: int = 0
    submitted_count: int = 0
    accepted_count: int = 0

    model_config = {"from_attributes": True}


class AssignmentDetailResponse(BaseModel):
    id: int
    title: str
    description: str
    status: str
    due_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    questions: list[AssignmentQuestionResponse]
    assigned_students: list[AssignmentStudentRef] = Field(default_factory=list)
    submissions: list[AssignmentSubmissionResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class AssignmentRunResultResponse(BaseModel):
    submission: AssignmentSubmissionResponse
    status: str
    results: list[dict[str, Any]]
    ai_review: Any = None
    decision_source: str | None = None
    manual_review_required: bool = False


class AssignmentAiHelpResponse(BaseModel):
    answer: str
    keywords: list[str] = Field(default_factory=list)
    facts: list[Any] = Field(default_factory=list)
    reasoning_trace: list[Any] = Field(default_factory=list)
    retrieval_trace: list[Any] = Field(default_factory=list)


class AssignmentGeneratedQuestionResponse(BaseModel):
    title: str
    prompt: str
    language: str = "java"
    test_cases: list[AssignmentTestCaseInput] = Field(default_factory=list)
    knowledge_node_ids: list[int] = Field(default_factory=list)
    knowledge_nodes: list[dict[str, Any]] = Field(default_factory=list)


class AssignmentGeneratedFocusResponse(BaseModel):
    ai_grading_focus: list[str] = Field(default_factory=list)
    summary: str = ""


class AssignmentProgressQuestionResponse(BaseModel):
    id: int
    title: str
    sort_order: int
    knowledge_nodes: list[dict[str, Any]] = Field(default_factory=list)


class AssignmentProgressStudentResponse(BaseModel):
    id: int
    username: str


class AssignmentProgressCellResponse(BaseModel):
    student_id: int
    question_id: int
    status: str
    submission_count: int = 0
    latest_submission_id: int | None = None
    submitted_at: datetime | None = None
    run_time_ms: int | None = None
    duration_seconds: int | None = None


class AssignmentProgressResponse(BaseModel):
    assignment_id: int
    title: str
    questions: list[AssignmentProgressQuestionResponse]
    students: list[AssignmentProgressStudentResponse]
    cells: list[AssignmentProgressCellResponse]


class AssignmentSubmissionDetailResponse(BaseModel):
    id: int
    assignment_id: int
    question_id: int
    question_title: str
    student_id: int
    student_username: str
    code: str
    status: str
    results_json: Any = None
    ai_review_json: Any = None
    decision_source: str | None = None
    manual_review_required: bool = False
    teacher_review_status: str | None = None
    teacher_review_note: str | None = None
    trust_label: str | None = None
    trust_score: float | None = None
    excluded_from_mastery_update: bool = False
    reviewed_at: datetime | None = None
    reviewed_by: int | None = None
    reviewed_by_username: str | None = None
    run_time_ms: int | None = None
    started_at: datetime | None = None
    duration_seconds: int | None = None
    submitted_at: datetime


class AssignmentReviewRequest(BaseModel):
    status: str = Field(pattern="^(accepted|ai_rejected|needs_manual_review)$")
    note: str = Field(default="", max_length=2000)
