from types import SimpleNamespace
from unittest.mock import Mock, patch

from backend.services.assignment_service import _mark_wrong_submission_bound_nodes_weak


def _relation(relation_id: int, sort_order: int, node_id: int, node_name: str):
    return SimpleNamespace(
        id=relation_id,
        sort_order=sort_order,
        knowledge_node_id=node_id,
        knowledge_node=SimpleNamespace(id=node_id, node_name=node_name),
    )


def test_accepted_submission_does_not_mark_weak_points() -> None:
    question = SimpleNamespace(knowledge_nodes=[_relation(1, 0, 10, "数组")])
    submission = SimpleNamespace(status="accepted")
    student = SimpleNamespace(id=1)

    with patch("backend.services.assignment_service.mark_node_weak") as mark_node_weak:
        _mark_wrong_submission_bound_nodes_weak(Mock(), student, question, submission)

    mark_node_weak.assert_not_called()


def test_wrong_submission_marks_all_bound_nodes_weak_once() -> None:
    question = SimpleNamespace(
        knowledge_nodes=[
            _relation(3, 2, 10, "数组"),
            _relation(1, 0, 20, "循环"),
            _relation(2, 1, 10, "数组"),
        ]
    )
    submission = SimpleNamespace(status="wrong_answer")
    student = SimpleNamespace(id=1)
    db = Mock()

    with patch("backend.services.assignment_service.mark_node_weak") as mark_node_weak:
        _mark_wrong_submission_bound_nodes_weak(db, student, question, submission)

    assert [call.args for call in mark_node_weak.call_args_list] == [
        (db, student, "循环"),
        (db, student, "数组"),
    ]


def test_wrong_submission_without_bound_nodes_is_noop() -> None:
    question = SimpleNamespace(knowledge_nodes=[])
    submission = SimpleNamespace(status="runtime_error")
    student = SimpleNamespace(id=1)

    with patch("backend.services.assignment_service.mark_node_weak") as mark_node_weak:
        _mark_wrong_submission_bound_nodes_weak(Mock(), student, question, submission)

    mark_node_weak.assert_not_called()
