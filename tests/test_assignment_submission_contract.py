from datetime import datetime
from types import SimpleNamespace

from backend.services.assignment_service import _submission_to_response


def test_submission_response_does_not_expose_legacy_trust_fields() -> None:
    submission = SimpleNamespace(
        id=1,
        assignment_id=2,
        question_id=3,
        student_id=4,
        code="class Main {}",
        answer_json=None,
        status="accepted",
        results_json=[],
        ai_review_json=None,
        final_decision_source="testcase",
        teacher_review_note=None,
        is_late=False,
        started_at=None,
        duration_seconds=12,
        submitted_at=datetime(2026, 5, 24, 12, 0, 0),
    )

    payload = _submission_to_response(submission).model_dump()

    assert "trust_label" not in payload
    assert "trust_score" not in payload
