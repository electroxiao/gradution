from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.api.deps import get_current_teacher, get_current_user, get_db
from backend.models.user import User
from backend.schemas.assignment import (
    AssignmentAiHelpRequest,
    AssignmentCreateRequest,
    AssignmentGenerateFocusRequest,
    AssignmentGenerateQuestionRequest,
    AssignmentGenerateTestCasesRequest,
    AssignmentQuestionsUpdateRequest,
    AssignmentReviewRequest,
    AssignmentSubmitRequest,
    AssignmentUpdateRequest,
)
from backend.services.assignment_service import (
    assignment_ai_help,
    assignment_ai_help_stream,
    create_assignment,
    generate_assignment_focus,
    generate_assignment_question,
    generate_assignment_test_cases,
    get_student_assignment_detail,
    get_teacher_assignment_detail,
    get_teacher_assignment_progress,
    get_teacher_submission_detail,
    list_student_assignments,
    list_student_submissions,
    list_teacher_assignments,
    review_assignment_submission,
    submit_assignment_question,
    update_assignment,
    update_assignment_questions,
)

teacher_router = APIRouter(prefix="/api/teacher/assignments", tags=["teacher-assignments"])
student_router = APIRouter(prefix="/api/assignments", tags=["assignments"])


@teacher_router.get("")
def get_teacher_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return list_teacher_assignments(db, current_user)


@teacher_router.post("")
def post_teacher_assignment(
    payload: AssignmentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return create_assignment(db, current_user, payload)


@teacher_router.post("/generate-question")
def post_generate_assignment_question(
    payload: AssignmentGenerateQuestionRequest,
    current_user: User = Depends(get_current_teacher),
):
    return generate_assignment_question(payload)


@teacher_router.post("/generate-testcases")
def post_generate_assignment_test_cases(
    payload: AssignmentGenerateTestCasesRequest,
    current_user: User = Depends(get_current_teacher),
):
    return generate_assignment_test_cases(payload)


@teacher_router.post("/generate-focus")
def post_generate_assignment_focus(
    payload: AssignmentGenerateFocusRequest,
    current_user: User = Depends(get_current_teacher),
):
    return generate_assignment_focus(payload)


@teacher_router.get("/{assignment_id}/progress")
def get_teacher_assignment_progress_view(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return get_teacher_assignment_progress(db, current_user, assignment_id)


@teacher_router.get("/{assignment_id}/submissions/{submission_id}")
def get_teacher_assignment_submission(
    assignment_id: int,
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return get_teacher_submission_detail(db, current_user, assignment_id, submission_id)


@teacher_router.post("/{assignment_id}/submissions/{submission_id}/review")
def post_teacher_assignment_submission_review(
    assignment_id: int,
    submission_id: int,
    payload: AssignmentReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return review_assignment_submission(db, current_user, assignment_id, submission_id, payload)


@teacher_router.get("/{assignment_id}")
def get_teacher_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return get_teacher_assignment_detail(db, current_user, assignment_id)


@teacher_router.patch("/{assignment_id}")
def patch_teacher_assignment(
    assignment_id: int,
    payload: AssignmentUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return update_assignment(db, current_user, assignment_id, payload)


@teacher_router.put("/{assignment_id}/questions")
def put_teacher_assignment_questions(
    assignment_id: int,
    payload: AssignmentQuestionsUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return update_assignment_questions(db, current_user, assignment_id, payload)


@student_router.get("")
def get_student_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_student_assignments(db, current_user)


@student_router.get("/{assignment_id}")
def get_student_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_student_assignment_detail(db, current_user, assignment_id)


@student_router.get("/{assignment_id}/submissions")
def get_assignment_submissions(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_student_submissions(db, current_user, assignment_id)


@student_router.post("/{assignment_id}/questions/{question_id}/submit")
def post_assignment_submission(
    assignment_id: int,
    question_id: int,
    payload: AssignmentSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return submit_assignment_question(db, current_user, assignment_id, question_id, payload.code, payload.started_at)


@student_router.post("/{assignment_id}/questions/{question_id}/ai-help")
def post_assignment_ai_help(
    assignment_id: int,
    question_id: int,
    payload: AssignmentAiHelpRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return assignment_ai_help(db, current_user, assignment_id, question_id, payload)


@student_router.post("/{assignment_id}/questions/{question_id}/ai-help/stream")
def post_assignment_ai_help_stream(
    assignment_id: int,
    question_id: int,
    payload: AssignmentAiHelpRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return StreamingResponse(
        assignment_ai_help_stream(db, current_user, assignment_id, question_id, payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
