from types import SimpleNamespace
from unittest.mock import Mock, patch

from backend.services.knowledge_progress_service import resolve_existing_graph_node_names
from backend.services.knowledge_state_service import _load_target_weak_point
from backend.services.weak_point_service import upsert_weak_points


class _FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def run(self, *_args, **_kwargs):
        return [
            {"name": "ArrayList"},
        ]


class _FakeDriver:
    def session(self, **_kwargs):
        return _FakeSession()

    def close(self):
        pass


def test_resolve_existing_graph_node_names_keeps_only_exact_graph_names() -> None:
    with patch("backend.services.knowledge_progress_service.GraphDatabase.driver", return_value=_FakeDriver()):
        assert resolve_existing_graph_node_names(["集合", "ArrayList", "集合"]) == ["ArrayList"]


def test_upsert_weak_points_only_marks_resolved_graph_nodes() -> None:
    db = Mock()
    user = SimpleNamespace(id=1)
    session = SimpleNamespace(id=2)

    with (
        patch("backend.services.weak_point_service.resolve_existing_graph_node_names", return_value=["ArrayList"]),
        patch("backend.services.weak_point_service.mark_node_weak", return_value=True) as mark_node_weak,
    ):
        added = upsert_weak_points(db, user, session, ["ArrayList", "不存在的临时概念"])

    assert added == ["ArrayList"]
    mark_node_weak.assert_called_once_with(db, user, "ArrayList", source_session_id=2)
    db.commit.assert_called_once()


def test_load_target_weak_point_matches_knowledge_node_id() -> None:
    weak_point = SimpleNamespace(id=100)
    node = SimpleNamespace(id=7, node_name="ArrayList")

    with patch("backend.services.knowledge_state_service.list_unmastered_weak_point_rows", return_value=[(weak_point, node)]):
        assert _load_target_weak_point(Mock(), SimpleNamespace(id=1), 7) == (weak_point, node, [(weak_point, node)])
