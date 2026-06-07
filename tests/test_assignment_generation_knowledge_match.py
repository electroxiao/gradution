from types import SimpleNamespace

from backend.schemas.assignment import AssignmentGenerateQuestionRequest
from backend.services import assignment_service


class _FakeChatCompletions:
    def __init__(self):
        self.last_messages = None

    def create(self, **kwargs):
        self.last_messages = kwargs["messages"]
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=(
                            '{"questions":[{'
                            '"title":"数组求和",'
                            '"prompt":"输入若干整数并输出总和。",'
                            '"question_type":"programming",'
                            '"language":"java",'
                            '"test_cases":[{"input_data":"3\\n1 2 3","expected_output":"6","is_sample":true,"sort_order":0}]'
                            "}]}"
                        )
                    )
                )
            ]
        )


class _FakeClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=_FakeChatCompletions())


def test_generate_assignment_questions_sends_requirement_matched_nodes_to_llm(monkeypatch):
    fake_client = _FakeClient()

    monkeypatch.setattr(assignment_service, "get_openai_client", lambda: fake_client)
    monkeypatch.setattr(
        assignment_service,
        "_match_assignment_requirement_knowledge_nodes",
        lambda db, payload: [
            {"id": 1, "node_name": "数组"},
            {"id": 2, "node_name": "for循环"},
        ],
    )
    monkeypatch.setattr(
        assignment_service,
        "_recommend_assignment_knowledge_nodes",
        lambda db, title, prompt, payload: [{"id": 1, "node_name": "数组"}],
    )

    assignment_service.generate_assignment_questions(
        db=SimpleNamespace(),
        payload=AssignmentGenerateQuestionRequest(
            requirement="围绕数组遍历生成一道练习题",
            programming_count=1,
            multiple_choice_count=0,
            fill_blank_count=0,
        ),
    )

    sent_prompt = fake_client.chat.completions.last_messages[0]["content"]
    assert "自动匹配知识点：数组、for循环" in sent_prompt


def test_generate_assignment_questions_binds_from_requirement_matches_before_prompt_scan(monkeypatch):
    fake_client = _FakeClient()

    monkeypatch.setattr(assignment_service, "get_openai_client", lambda: fake_client)
    monkeypatch.setattr(
        assignment_service,
        "_match_assignment_requirement_knowledge_nodes",
        lambda db, payload: [
            {"id": 10, "node_name": "继承"},
            {"id": 11, "node_name": "方法重写"},
        ],
    )

    def fail_if_prompt_scan_runs(*args, **kwargs):
        raise AssertionError("generated question binding should not scan the whole graph when requirement matches exist")

    monkeypatch.setattr(assignment_service, "_recommend_assignment_knowledge_nodes", fail_if_prompt_scan_runs)

    result = assignment_service.generate_assignment_questions(
        db=SimpleNamespace(),
        payload=AssignmentGenerateQuestionRequest(
            requirement="围绕继承生成一道练习题",
            programming_count=1,
            multiple_choice_count=0,
            fill_blank_count=0,
        ),
    )

    assert result.questions[0]["knowledge_node_ids"] == [10, 11]
    assert result.questions[0]["knowledge_nodes"] == [
        {"id": 10, "node_name": "继承"},
        {"id": 11, "node_name": "方法重写"},
    ]


def test_requirement_graph_match_uses_keywords_and_returns_seed_nodes(monkeypatch):
    captured = {}

    def fake_query_seed_nodes(driver, question, keywords, limit_per_kw, max_total):
        captured["driver"] = driver
        captured["question"] = question
        captured["keywords"] = keywords
        captured["limit_per_kw"] = limit_per_kw
        captured["max_total"] = max_total
        return [
            {"name": "数组", "desc": "顺序存储结构"},
            {"name": "for循环", "desc": "循环控制结构"},
        ]

    monkeypatch.setattr(assignment_service, "get_neo4j_driver", lambda: "driver")
    monkeypatch.setattr(assignment_service.rag_engine, "_query_seed_nodes", fake_query_seed_nodes)

    node_names = assignment_service._match_assignment_requirement_graph_nodes(
        search_text="围绕数组遍历生成一道练习题",
        keywords=["数组", "循环"],
        explicit_terms=["数组"],
        limit=5,
    )

    assert node_names == ["数组", "for循环"]
    assert captured["driver"] == "driver"
    assert captured["question"] == "围绕数组遍历生成一道练习题"
    assert captured["keywords"][:2] == ["数组", "循环"]
    assert captured["keywords"].count("数组") == 1
    assert captured["max_total"] == 5
