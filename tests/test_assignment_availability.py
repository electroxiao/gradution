from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.services.assignment_service import (
    _assignment_has_started,
    _assignment_is_late,
    _ensure_assignment_started,
)


def test_assignment_without_start_time_has_started() -> None:
    assignment = SimpleNamespace(starts_at=None)

    assert _assignment_has_started(assignment, datetime(2026, 5, 16, 9, 0, 0)) is True


def test_future_start_assignment_is_rejected() -> None:
    now = datetime(2026, 5, 16, 9, 0, 0)
    assignment = SimpleNamespace(starts_at=now + timedelta(hours=1))

    with pytest.raises(HTTPException) as error:
        _ensure_assignment_started(assignment, now)

    assert error.value.status_code == 403
    assert error.value.detail == "作业尚未开始。"


def test_due_assignment_is_marked_late_after_deadline() -> None:
    now = datetime(2026, 5, 16, 9, 0, 0)
    assignment = SimpleNamespace(due_at=now - timedelta(seconds=1))

    assert _assignment_is_late(assignment, now) is True


def test_due_assignment_is_not_late_before_deadline() -> None:
    now = datetime(2026, 5, 16, 9, 0, 0)
    assignment = SimpleNamespace(due_at=now + timedelta(seconds=1))

    assert _assignment_is_late(assignment, now) is False
