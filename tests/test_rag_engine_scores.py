import pytest

from backend.services import rag_engine


class FakeSession:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def run(self, query, **kwargs):
        return self.rows


class FakeDriver:
    def __init__(self, rows):
        self.rows = rows

    def session(self, database=None):
        return FakeSession(self.rows)


@pytest.mark.parametrize(
    ("match_score", "match_type"),
    [
        (1.0, "exact_name"),
        (0.75, "name_contains"),
        (0.5, "desc_match"),
    ],
)
def test_query_seed_nodes_uses_normalized_match_scores(match_score, match_type):
    seeds = rag_engine._query_seed_nodes(
        FakeDriver([{"name": "数组越界异常", "desc": "访问数组时下标超出范围", "match_score": match_score}]),
        "为什么会出现数组越界异常",
        ["数组"],
        limit_per_kw=3,
        max_total=3,
    )

    assert seeds[0]["match_score"] == match_score
    assert seeds[0]["match_type"] == match_type


def test_query_subgraph_nodes_uses_normalized_keyword_scores(monkeypatch):
    monkeypatch.setattr(rag_engine, "_token_overlap_score", lambda question, text: 0.0)

    nodes = rag_engine._query_subgraph_nodes(
        FakeDriver([{"name": "数组下标", "desc": "数组元素的位置编号", "match_score": 0.75}]),
        "为什么数组下标会越界",
        ["数组"],
        seeds=[],
        max_nodes=3,
    )

    assert nodes == [
        {
            "name": "数组下标",
            "desc": "数组元素的位置编号",
            "score": pytest.approx(0.45),
            "source": "keyword",
        }
    ]
