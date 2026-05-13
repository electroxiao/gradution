from types import SimpleNamespace
from unittest.mock import Mock, patch

from backend.services.knowledge_state_service import _query_candidate_nodes, get_weak_points_graph
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


class _GraphRecordList(list):
    def single(self):
        return self[0] if self else None


class _WeakGraphSession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def run(self, query, **_kwargs):
        if "LIMIT 1" in query:
            return _GraphRecordList([
                {"name": "ArrayList", "desc": "动态数组", "labels": ["Knowledge"]},
            ])
        return _GraphRecordList([])


class _WeakGraphDriver:
    def session(self, **_kwargs):
        return _WeakGraphSession()

    def close(self):
        pass


class _CandidateSession:
    def __init__(self):
        self.queries = []

    def run(self, query, **kwargs):
        self.queries.append(query)
        if "DEPENDS_ON" in query and "neighbor.name" in query:
            limit = kwargs.get("limit", 6)
            return [
                {
                    "name": f"依赖{i}",
                    "desc": "",
                    "labels": ["Knowledge"],
                    "relation": "DEPENDS_ON",
                    "direction": "in",
                }
                for i in range(limit)
            ]
        return []


def test_resolve_existing_graph_node_names_keeps_only_exact_graph_names() -> None:
    with patch("backend.services.knowledge_progress_service.get_neo4j_driver", return_value=_FakeDriver()):
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


def test_weak_points_graph_reuses_loaded_weak_rows_for_state_map() -> None:
    db = Mock()
    user = SimpleNamespace(id=1)
    weak_point = SimpleNamespace(id=100)
    node = SimpleNamespace(id=7, node_name="ArrayList")
    weak_rows = [(weak_point, node)]

    with (
        patch("backend.services.knowledge_state_service.list_unmastered_weak_point_rows", return_value=weak_rows),
        patch("backend.services.knowledge_state_service.build_graph_state_map", return_value={}) as build_state_map,
        patch("backend.services.knowledge_state_service.get_neo4j_driver", return_value=_WeakGraphDriver()) as get_driver,
    ):
        result = get_weak_points_graph(db, user, weak_point_id=7)

    assert result["target"]["name"] == "ArrayList"
    build_state_map.assert_called_once_with(db, user, weak_rows=weak_rows)
    get_driver.assert_called_once_with()


def test_query_candidate_nodes_skips_keyword_scan_when_dependency_candidates_fill_limit() -> None:
    session = _CandidateSession()

    candidates = _query_candidate_nodes(session, "ArrayList", "动态数组", limit=3)

    assert [item["name"] for item in candidates] == ["依赖0", "依赖1", "依赖2"]
    assert len(session.queries) == 1
