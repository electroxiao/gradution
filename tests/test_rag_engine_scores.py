from backend.services import rag_engine


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def run(self, query, **kwargs):
        self.calls.append({"query": query, "kwargs": kwargs})
        return self.responses[len(self.calls) - 1]


class FakeDriver:
    def __init__(self, responses):
        self.responses = responses
        self.last_session = None

    def session(self, database=None):
        self.last_session = FakeSession(self.responses)
        return self.last_session


def test_query_keyword_neighborhood_returns_seed_related_nodes_and_seed_edges_only():
    driver = FakeDriver(
        [
            [
                {
                    "seed": "多线程",
                    "seed_desc": "同时运行多个执行路径。",
                }
            ],
            [
                {"name": "多线程", "desc": "同时运行多个执行路径。"},
                {"name": "锁(Lock)", "desc": "控制共享资源访问。"},
                {"name": "线程", "desc": "程序调度的基本执行单元。"},
            ],
            [
                {
                    "source": "多线程",
                    "source_desc": "同时运行多个执行路径。",
                    "relation": "DEPENDS_ON",
                    "direction": "in",
                    "target": "锁(Lock)",
                    "target_desc": "控制共享资源访问。",
                },
                {
                    "source": "锁(Lock)",
                    "source_desc": "控制共享资源访问。",
                    "relation": "DEPENDS_ON",
                    "direction": "out",
                    "target": "线程",
                    "target_desc": "程序调度的基本执行单元。",
                },
            ],
        ]
    )

    result = rag_engine._query_keyword_neighborhood(driver, ["多线程", "Lock"], max_depth=2)

    seeds = [fact for fact in result if fact["type"] == "seed"]
    related_nodes = [fact for fact in result if fact["type"] == "related_node"]
    paths = [fact for fact in result if fact["type"] == "path"]

    assert seeds == [
        {
            "type": "seed",
            "seed": "多线程",
            "keyword": "多线程, Lock",
            "desc": "同时运行多个执行路径。",
            "score": 1.0,
            "match_type": "keyword_match",
        }
    ]
    assert {"type": "related_node", "name": "锁(Lock)", "desc": "控制共享资源访问。"} in related_nodes
    assert {"type": "related_node", "name": "线程", "desc": "程序调度的基本执行单元。"} in related_nodes
    assert any(path["path_text"] == "多线程 -> (DEPENDS_ON,in) -> 锁(Lock)" for path in paths)
    assert not any(path["path_text"] == "锁(Lock) -> (DEPENDS_ON,out) -> 线程" for path in paths)
    assert driver.last_session.calls[1]["kwargs"] == {"seed_names": ["多线程"]}
    assert driver.last_session.calls[2]["kwargs"] == {"node_names": ["多线程", "锁(Lock)", "线程"], "seed_names": ["多线程"]}


def test_query_keyword_neighborhood_applies_related_node_and_path_limits():
    driver = FakeDriver(
        [
            [{"seed": "多线程", "seed_desc": "同时运行多个执行路径。"}],
            [
                {"name": "多线程", "desc": "同时运行多个执行路径。"},
                {"name": "锁(Lock)", "desc": "控制共享资源访问。"},
                {"name": "线程", "desc": "程序调度的基本执行单元。"},
                {"name": "阻塞(Blocking)", "desc": "线程等待资源。"},
            ],
            [
                {
                    "source": "多线程",
                    "source_desc": "同时运行多个执行路径。",
                    "relation": "DEPENDS_ON",
                    "direction": "in",
                    "target": "锁(Lock)",
                    "target_desc": "控制共享资源访问。",
                },
                {
                    "source": "多线程",
                    "source_desc": "同时运行多个执行路径。",
                    "relation": "DEPENDS_ON",
                    "direction": "in",
                    "target": "线程",
                    "target_desc": "程序调度的基本执行单元。",
                },
            ],
        ]
    )

    result = rag_engine._query_keyword_neighborhood(
        driver,
        ["多线程"],
        max_depth=2,
        max_related_nodes=2,
        max_paths=1,
    )

    assert len([fact for fact in result if fact["type"] == "related_node"]) == 2
    assert len([fact for fact in result if fact["type"] == "path"]) == 1


def test_query_graph_with_reasoning_uses_keyword_neighborhood_without_path_selection(monkeypatch):
    called = {}

    def fake_neighborhood(driver, keywords, max_depth=2):
        called["keywords"] = keywords
        called["max_depth"] = max_depth
        return [
            {
                "type": "seed",
                "seed": "多线程",
                "keyword": "多线程",
                "desc": "同时运行多个执行路径。",
                "score": 1.0,
                "match_type": "keyword_match",
            },
            {
                "type": "related_node",
                "name": "锁(Lock)",
                "desc": "控制共享资源访问。",
            },
        ]

    monkeypatch.setattr(rag_engine, "_query_keyword_neighborhood", fake_neighborhood)

    reasoning_trace = []
    retrieval_trace = []
    result = rag_engine.query_graph_with_reasoning(
        driver=object(),
        client=object(),
        question="Java 多线程中 Lock 怎么保证线程安全？",
        keywords=["Lock", "多线程"],
        max_depth=2,
        width=3,
        reasoning_trace=reasoning_trace,
        retrieval_trace=retrieval_trace,
    )

    assert called == {"keywords": ["Lock", "多线程"], "max_depth": 2}
    assert any(fact["type"] == "related_node" and fact["name"] == "锁(Lock)" for fact in result)
    assert any(fact["type"] == "summary" and "related_nodes=1" in fact["text"] for fact in result)
    assert retrieval_trace[0]["title"] == "两跳子图检索"
