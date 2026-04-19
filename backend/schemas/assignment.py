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
    language: str = Field(default="java", max_length=32)
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


class AssignmentSubmitRequest(BaseModel):
    code: str = Field(min_length=1)


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
    language: str
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


class AssignmentAiHelpResponse(BaseModel):
    answer: str


class AssignmentGeneratedQuestionResponse(BaseModel):
    title: str
    prompt: str
    language: str = "java"
    test_cases: list[AssignmentTestCaseInput] = Field(default_factory=list)
