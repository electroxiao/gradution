import importlib
import inspect as py_inspect
from datetime import datetime

import pytest
from fastapi import HTTPException
from fastapi.params import Query
from sqlalchemy import create_engine, inspect as sqlalchemy_inspect
from sqlalchemy.orm import sessionmaker

from backend.db import base as model_base  # noqa: F401
from backend.db.bootstrap import ensure_schema_and_seed
from backend.db.bootstrap import (
    _chat_knowledge_events_id_needs_autoincrement,
    _ensure_chat_knowledge_events_table,
    _legacy_chat_knowledge_event_columns,
)
from backend.db.session import Base
from backend.models.chat import ChatKnowledgeEvent, ChatMessage, ChatSession
from backend.models.knowledge import KnowledgeNode, UserWeakPoint
from backend.models.knowledge_state import UserKnowledgeState
from backend.models.user import User
from backend.api.routes import chat as chat_routes
from backend.api.routes import teacher as teacher_routes
from backend.schemas.chat import ChatConsultationEventResponse, MessageCreateRequest
from backend.schemas.teacher import TeacherConsultationSummaryResponse
from backend.services import chat_service, rag_engine
from backend.services.chat_knowledge_event_service import (
    ConsultationEventSummary,
    ConsultationSummary,
    _parse_candidate_json,
    extract_candidates_from_turn,
    list_recent_consultations,
    list_student_consultations,
    list_teacher_consultation_hotspots,
    record_turn_knowledge_events,
)


class FakeChoice:
    def __init__(self, content):
        self.message = type("Message", (), {"content": content})()


class FakeResponse:
    def __init__(self, content):
        self.choices = [FakeChoice(content)]


class FakeCompletions:
    def __init__(self, content):
        self.content = content

    def create(self, **kwargs):
        return FakeResponse(self.content)


class FakeClient:
    def __init__(self, content):
        self.chat = type("Chat", (), {"completions": FakeCompletions(content)})()


class CapturingCompletions:
    def __init__(self, content):
        self.content = content
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeResponse(self.content)


class CapturingClient:
    def __init__(self, content):
        self.completions = CapturingCompletions(content)
        self.chat = type("Chat", (), {"completions": self.completions})()


class FakeStreamDelta:
    def __init__(self, content):
        self.content = content


class FakeStreamChoice:
    def __init__(self, content):
        self.delta = FakeStreamDelta(content)


class FakeStreamChunk:
    def __init__(self, content):
        self.choices = [FakeStreamChoice(content)]


class FakeStreamCompletions:
    def create(self, **kwargs):
        if kwargs.get("stream"):
            return iter([FakeStreamChunk("直接"), FakeStreamChunk("回答")])
        return FakeResponse("标题")


class FakeStreamClient:
    def __init__(self):
        self.chat = type("Chat", (), {"completions": FakeStreamCompletions()})()


class RaisingStreamCompletions:
    def create(self, **kwargs):
        if not kwargs.get("stream"):
            return FakeResponse("标题")

        def stream():
            yield FakeStreamChunk("半句")
            raise RuntimeError("stream failed")

        return stream()


class RaisingStreamClient:
    def __init__(self):
        self.chat = type("Chat", (), {"completions": RaisingStreamCompletions()})()


class EmptyChoicesClient:
    def __init__(self):
        completions = type(
            "Completions",
            (),
            {"create": lambda self, **kwargs: type("Response", (), {"choices": []})()},
        )()
        self.chat = type("Chat", (), {"completions": completions})()


class RaisingCompletions:
    def create(self, **kwargs):
        raise RuntimeError("LLM unavailable")


class RaisingClient:
    def __init__(self):
        self.chat = type("Chat", (), {"completions": RaisingCompletions()})()


@pytest.fixture(scope="session", autouse=True)
def backend_ready():
    return None


@pytest.fixture(scope="session", autouse=True)
def clean_auto_test_data():
    return None


@pytest.fixture()
def isolated_engine():
    test_engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=test_engine)
    try:
        yield test_engine
    finally:
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def isolated_db(isolated_engine):
    TestingSessionLocal = sessionmaker(bind=isolated_engine, autoflush=False, autocommit=False, future=True)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _student(db, username="student", class_name="Class A"):
    user = User(username=username, password_hash="hash", role="student", class_name=class_name)
    db.add(user)
    db.flush()
    return user


def _teacher(db, username="teacher"):
    user = User(username=username, password_hash="hash", role="teacher")
    db.add(user)
    db.flush()
    return user


def _node(db, name):
    node = KnowledgeNode(node_name=name)
    db.add(node)
    db.flush()
    return node


def _turn(db, user, title="Java 咨询"):
    session = ChatSession(user_id=user.id, title=title)
    db.add(session)
    db.flush()
    user_message = ChatMessage(session_id=session.id, role="user", content="为什么会空指针？")
    assistant_message = ChatMessage(session_id=session.id, role="assistant", content="需要先判断对象是否为 null。")
    db.add_all([user_message, assistant_message])
    db.flush()
    return session, user_message, assistant_message


def test_chat_knowledge_events_table_exists_after_bootstrap(isolated_engine):
    ensure_schema_and_seed(isolated_engine)
    inspector = sqlalchemy_inspect(isolated_engine)

    assert "chat_knowledge_events" in inspector.get_table_names()


def test_chat_knowledge_event_model_has_expected_columns():
    columns = {column.name for column in ChatKnowledgeEvent.__table__.columns}

    assert {
        "id",
        "user_id",
        "session_id",
        "user_message_id",
        "assistant_message_id",
        "knowledge_node_id",
        "created_at",
    }.issubset(columns)
    assert "confidence" not in columns
    assert "evidence_text" not in columns


def test_chat_knowledge_event_id_is_autoincrementing():
    assert ChatKnowledgeEvent.__table__.c.id.autoincrement is True


def test_chat_knowledge_events_existing_table_detects_missing_id_autoincrement():
    assert _chat_knowledge_events_id_needs_autoincrement(
        [{"name": "id", "autoincrement": False}, {"name": "user_id"}]
    )
    assert not _chat_knowledge_events_id_needs_autoincrement(
        [{"name": "id", "autoincrement": True}, {"name": "user_id"}]
    )


def test_chat_knowledge_events_detects_legacy_detail_columns():
    assert _legacy_chat_knowledge_event_columns(
        [{"name": "id"}, {"name": "confidence"}, {"name": "evidence_text"}]
    ) == ["confidence", "evidence_text"]
    assert _legacy_chat_knowledge_event_columns([{"name": "id"}, {"name": "user_id"}]) == []


def test_bootstrap_helper_creates_chat_knowledge_events_with_model_constraints():
    test_engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=test_engine)
    ChatKnowledgeEvent.__table__.drop(bind=test_engine)

    _ensure_chat_knowledge_events_table(test_engine)

    inspector = sqlalchemy_inspect(test_engine)
    assert "chat_knowledge_events" in inspector.get_table_names()

    columns = {column["name"] for column in inspector.get_columns("chat_knowledge_events")}
    assert {
        "id",
        "user_id",
        "session_id",
        "user_message_id",
        "assistant_message_id",
        "knowledge_node_id",
        "created_at",
    }.issubset(columns)
    assert "confidence" not in columns
    assert "evidence_text" not in columns

    unique_constraints = {
        constraint["name"]: set(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("chat_knowledge_events")
    }
    assert unique_constraints["uq_chat_knowledge_event_turn_node"] == {
        "user_id",
        "session_id",
        "user_message_id",
        "assistant_message_id",
        "knowledge_node_id",
    }

    foreign_keys = {
        (foreign_key["referred_table"], tuple(foreign_key["constrained_columns"]))
        for foreign_key in inspector.get_foreign_keys("chat_knowledge_events")
    }
    assert {
        ("users", ("user_id",)),
        ("chat_sessions", ("session_id",)),
        ("chat_messages", ("user_message_id",)),
        ("chat_messages", ("assistant_message_id",)),
        ("knowledge_nodes", ("knowledge_node_id",)),
    }.issubset(foreign_keys)

    indexes = {index["name"] for index in inspector.get_indexes("chat_knowledge_events")}
    assert {
        "ix_chat_knowledge_events_user_id",
        "ix_chat_knowledge_events_session_id",
        "ix_chat_knowledge_events_user_message_id",
        "ix_chat_knowledge_events_assistant_message_id",
        "ix_chat_knowledge_events_knowledge_node_id",
    }.issubset(indexes)


def test_backend_main_imports_after_chat_decoupling():
    assert importlib.import_module("backend.main")


def test_consultation_api_routes_are_registered():
    app = importlib.import_module("backend.main").app
    route_paths = {route.path for route in app.routes}

    assert "/api/chat/consultations/recent" in route_paths
    assert "/api/teacher/consultations/hotspots" in route_paths
    assert "/api/teacher/students/{student_id}/consultations" in route_paths


def test_consultation_routes_use_query_bounds_for_limits():
    endpoints = [
        (chat_routes.get_recent_consultations, 20),
        (teacher_routes.get_consultation_hotspots, 10),
        (teacher_routes.get_student_consultations, 20),
    ]

    for endpoint, default_limit in endpoints:
        limit = py_inspect.signature(endpoint).parameters["limit"].default
        assert isinstance(limit, Query)
        assert limit.default == default_limit
        metadata = {type(item).__name__: item for item in limit.metadata}
        assert metadata["Ge"].ge == 1
        assert metadata["Le"].le == 50


def test_teacher_student_consultations_rejects_missing_or_non_student_user(isolated_db):
    teacher = _teacher(isolated_db)

    with pytest.raises(HTTPException) as exc_info:
        teacher_routes.get_student_consultations(
            teacher.id,
            db=isolated_db,
            current_user=teacher,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "学生不存在"


def test_consultation_response_schemas_serialize_service_summaries():
    now = datetime(2026, 5, 15, 12, 0, 0)
    recent = ConsultationEventSummary(
        event_id=1,
        session_id=2,
        session_title="Java 咨询",
        user_message_id=3,
        assistant_message_id=4,
        node_id=5,
        node_name="空指针异常",
        created_at=now,
    )
    hotspot = ConsultationSummary(
        node_id=5,
        node_name="空指针异常",
        mention_count=2,
        student_count=1,
        last_seen_at=now,
    )

    recent_response = ChatConsultationEventResponse(
        id=recent.event_id,
        knowledge_node_id=recent.node_id,
        node_name=recent.node_name,
        session_id=recent.session_id,
        session_title=recent.session_title,
        created_at=recent.created_at,
    )
    hotspot_response = TeacherConsultationSummaryResponse(
        knowledge_node_id=hotspot.node_id,
        node_name=hotspot.node_name,
        mention_count=hotspot.mention_count,
        student_count=hotspot.student_count,
        last_seen_at=hotspot.last_seen_at,
    )

    assert recent_response.model_dump() == {
        "id": 1,
        "knowledge_node_id": 5,
        "node_name": "空指针异常",
        "session_id": 2,
        "session_title": "Java 咨询",
        "created_at": now,
    }
    assert hotspot_response.model_dump() == {
        "knowledge_node_id": 5,
        "node_name": "空指针异常",
        "mention_count": 2,
        "student_count": 1,
        "last_seen_at": now,
    }


def test_extract_candidates_from_turn_parses_json_from_fake_openai_client():
    client = FakeClient(
        """
        下面是抽取结果：
        [
          {"name": "空指针异常"},
          {"name": "数组"}
        ]
        """
    )

    candidates = extract_candidates_from_turn(
        client,
        user_content="为什么我的对象调用方法会报 NullPointerException？",
        assistant_content="先判断对象是否为 null，再调用方法。",
        previous_context="Java 异常处理",
    )

    assert candidates == [
        {"name": "空指针异常"},
        {"name": "数组"},
    ]


def test_extract_candidates_from_turn_uses_formal_nodes_as_allowed_options():
    client = CapturingClient('[{"node_id": 7, "node_name": "封装(Encapsulation)"}]')

    candidates = extract_candidates_from_turn(
        client,
        user_content="private 为什么外部不能访问？",
        assistant_content="这是封装和访问控制。",
        formal_nodes=[{"id": 7, "name": "封装(Encapsulation)"}, {"id": 8, "name": "继承(Inheritance)"}],
    )

    prompt = client.completions.calls[0]["messages"][0]["content"]
    assert "只能从下面的正式知识图谱节点中选择" in prompt
    assert '{"id":7,"name":"封装(Encapsulation)"}' in prompt
    assert "confidence" not in prompt
    assert "evidence" not in prompt
    assert candidates == [
        {"node_id": 7, "node_name": "封装(Encapsulation)", "name": "封装(Encapsulation)"}
    ]


@pytest.mark.parametrize("content", [None, 123])
def test_extract_candidates_from_turn_handles_empty_or_non_text_content(content):
    assert (
        extract_candidates_from_turn(
            FakeClient(content),
            user_content="为什么报错？",
            assistant_content="需要查看异常信息。",
        )
        == []
    )


def test_parse_candidate_json_returns_empty_for_non_string_content():
    assert _parse_candidate_json({"name": "数组"}) == []


def test_extract_candidates_from_turn_returns_empty_for_sdk_exception():
    assert (
        extract_candidates_from_turn(
            RaisingClient(),
            user_content="ArrayList 为什么报错？",
            assistant_content="需要检查泛型和下标。",
        )
        == []
    )


def test_extract_candidates_from_turn_returns_empty_for_empty_choices():
    assert (
        extract_candidates_from_turn(
            EmptyChoicesClient(),
            user_content="ArrayList 为什么报错？",
            assistant_content="需要检查泛型和下标。",
        )
        == []
    )


def test_record_turn_knowledge_events_only_writes_existing_nodes_and_leaves_progress_tables_untouched(isolated_db):
    user = _student(isolated_db)
    _node(isolated_db, "空指针异常")
    session, user_message, assistant_message = _turn(isolated_db, user)

    inserted = record_turn_knowledge_events(
        isolated_db,
        FakeClient(
            """
            [
              {"name": "空指针异常"},
              {"name": "不存在的概念"}
            ]
            """
        ),
        user,
        session,
        user_message,
        assistant_message,
    )

    assert inserted == ["空指针异常"]
    assert isolated_db.query(ChatKnowledgeEvent).count() == 1
    assert isolated_db.query(KnowledgeNode).count() == 1
    assert isolated_db.query(UserWeakPoint).count() == 0
    assert isolated_db.query(UserKnowledgeState).count() == 0


def test_record_turn_knowledge_events_prefers_formal_node_ids_from_extractor(isolated_db):
    user = _student(isolated_db)
    node = _node(isolated_db, "封装(Encapsulation)")
    _node(isolated_db, "继承(Inheritance)")
    session, user_message, assistant_message = _turn(isolated_db, user)
    client = CapturingClient(
        f'[{{"node_id": {node.id}, "node_name": "封装(Encapsulation)"}}]'
    )

    inserted = record_turn_knowledge_events(
        isolated_db,
        client,
        user,
        session,
        user_message,
        assistant_message,
    )

    prompt = client.completions.calls[0]["messages"][0]["content"]
    assert f'{{"id":{node.id},"name":"封装(Encapsulation)"}}' in prompt
    assert inserted == ["封装(Encapsulation)"]
    event = isolated_db.query(ChatKnowledgeEvent).one()
    assert event.knowledge_node_id == node.id


def test_record_turn_knowledge_events_requires_python_exact_node_name_match(isolated_db):
    user = _student(isolated_db)
    _node(isolated_db, "arraylist")
    session, user_message, assistant_message = _turn(isolated_db, user)

    inserted = record_turn_knowledge_events(
        isolated_db,
        FakeClient('[{"name": "ArrayList"}]'),
        user,
        session,
        user_message,
        assistant_message,
    )

    assert inserted == []
    assert isolated_db.query(ChatKnowledgeEvent).count() == 0


def test_record_turn_knowledge_events_resolves_common_aliases_to_formal_nodes(isolated_db):
    user = _student(isolated_db)
    for name in ["封装(Encapsulation)", "main方法", "继承(Inheritance)", "多态(Polymorphism)"]:
        _node(isolated_db, name)
    session, user_message, assistant_message = _turn(isolated_db, user)

    inserted = record_turn_knowledge_events(
        isolated_db,
        FakeClient(
            """
            [
              {"name": "封装"},
              {"name": "main函数"},
              {"name": "继承"},
              {"name": "多态"}
            ]
            """
        ),
        user,
        session,
        user_message,
        assistant_message,
    )

    assert inserted == ["封装(Encapsulation)", "main方法", "继承(Inheritance)", "多态(Polymorphism)"]
    assert isolated_db.query(ChatKnowledgeEvent).count() == 4


def test_record_turn_knowledge_events_is_idempotent_for_same_turn_and_node(isolated_db):
    user = _student(isolated_db)
    _node(isolated_db, "循环")
    session, user_message, assistant_message = _turn(isolated_db, user)
    client = FakeClient('[{"name": "循环"}]')

    first_inserted = record_turn_knowledge_events(
        isolated_db,
        client,
        user,
        session,
        user_message,
        assistant_message,
    )
    second_inserted = record_turn_knowledge_events(
        isolated_db,
        client,
        user,
        session,
        user_message,
        assistant_message,
    )

    assert first_inserted == ["循环"]
    assert second_inserted == []
    assert isolated_db.query(ChatKnowledgeEvent).count() == 1


def test_stream_message_answers_without_pre_response_graph_retrieval(isolated_db, monkeypatch):
    user = _student(isolated_db)
    session = ChatSession(user_id=user.id, title="已有对话")
    isolated_db.add(session)
    isolated_db.flush()
    graph_calls = {"keywords": 0, "graph": 0}

    def fake_extract_keywords(*args, **kwargs):
        graph_calls["keywords"] += 1
        return ["空指针异常"]

    def fake_query_graph(*args, **kwargs):
        graph_calls["graph"] += 1
        return []

    monkeypatch.setattr(chat_service, "get_openai_client", lambda: FakeStreamClient())
    monkeypatch.setattr(rag_engine, "extract_keywords_with_llm", fake_extract_keywords)
    monkeypatch.setattr(rag_engine, "query_graph_with_reasoning", fake_query_graph)
    monkeypatch.setattr(rag_engine, "ask_deepseek_stream", lambda *args, **kwargs: iter(["旧路径"]))
    monkeypatch.setattr(
        chat_service,
        "_schedule_turn_knowledge_extraction",
        lambda *args, **kwargs: None,
        raising=False,
    )

    events = list(
        chat_service.stream_message(
            isolated_db,
            user,
            session.id,
            MessageCreateRequest(content="为什么会空指针？"),
        )
    )

    assert graph_calls == {"keywords": 0, "graph": 0}
    assert any(event.startswith("event: assistant_delta") for event in events)
    assert any(event.startswith("event: assistant_done") for event in events)


def test_stream_message_schedules_extraction_before_assistant_done(isolated_db, monkeypatch):
    user = _student(isolated_db)
    session = ChatSession(user_id=user.id, title="已有对话")
    isolated_db.add(session)
    isolated_db.flush()
    sequence = []

    monkeypatch.setattr(chat_service, "get_openai_client", lambda: FakeStreamClient())
    monkeypatch.setattr(
        chat_service,
        "_schedule_turn_knowledge_extraction",
        lambda *args, **kwargs: sequence.append("scheduled"),
    )

    for event in chat_service.stream_message(
        isolated_db,
        user,
        session.id,
        MessageCreateRequest(content="为什么会空指针？"),
    ):
        if event.startswith("event: assistant_done"):
            sequence.append("assistant_done")

    assert sequence == ["scheduled", "assistant_done"]


def test_stream_message_rolls_back_and_yields_error_when_direct_stream_fails(isolated_db, monkeypatch):
    user = _student(isolated_db)
    session = ChatSession(user_id=user.id, title="已有对话")
    isolated_db.add(session)
    isolated_db.commit()
    session_id = session.id
    scheduled = []

    monkeypatch.setattr(chat_service, "get_openai_client", lambda: RaisingStreamClient())
    monkeypatch.setattr(
        chat_service,
        "_schedule_turn_knowledge_extraction",
        lambda *args, **kwargs: scheduled.append(kwargs),
    )

    events = list(
        chat_service.stream_message(
            isolated_db,
            user,
            session_id,
            MessageCreateRequest(content="为什么会空指针？"),
        )
    )

    assert any(event.startswith("event: error") for event in events)
    assert not any(event.startswith("event: assistant_done") for event in events)
    assert scheduled == []
    assert isolated_db.query(ChatMessage).filter(ChatMessage.session_id == session_id).count() == 0


def test_consultation_summaries_group_recent_student_and_teacher_views(isolated_db):
    alice = _student(isolated_db, "alice", "Class A")
    bob = _student(isolated_db, "bob", "Class A")
    charlie = _student(isolated_db, "charlie", "Class B")
    _teacher(isolated_db)
    loops = _node(isolated_db, "循环")
    arrays = _node(isolated_db, "数组")

    alice_session, alice_user_message, alice_assistant_message = _turn(isolated_db, alice, "Alice 第一轮")
    bob_session, bob_user_message, bob_assistant_message = _turn(isolated_db, bob, "Bob 第一轮")
    charlie_session, charlie_user_message, charlie_assistant_message = _turn(isolated_db, charlie, "Charlie 第一轮")
    isolated_db.add_all(
        [
            ChatKnowledgeEvent(
                user_id=alice.id,
                session_id=alice_session.id,
                user_message_id=alice_user_message.id,
                assistant_message_id=alice_assistant_message.id,
                knowledge_node_id=loops.id,
            ),
            ChatKnowledgeEvent(
                user_id=alice.id,
                session_id=alice_session.id,
                user_message_id=alice_user_message.id,
                assistant_message_id=alice_assistant_message.id,
                knowledge_node_id=arrays.id,
            ),
            ChatKnowledgeEvent(
                user_id=bob.id,
                session_id=bob_session.id,
                user_message_id=bob_user_message.id,
                assistant_message_id=bob_assistant_message.id,
                knowledge_node_id=loops.id,
            ),
            ChatKnowledgeEvent(
                user_id=charlie.id,
                session_id=charlie_session.id,
                user_message_id=charlie_user_message.id,
                assistant_message_id=charlie_assistant_message.id,
                knowledge_node_id=arrays.id,
            ),
        ]
    )
    isolated_db.flush()

    recent = list_recent_consultations(isolated_db, alice, limit=5)
    assert [(item.node_name, item.session_title) for item in recent] == [
        ("数组", "Alice 第一轮"),
        ("循环", "Alice 第一轮"),
    ]

    student_summary = list_student_consultations(isolated_db, alice.id, limit=5)
    assert [(item.node_name, item.mention_count, item.student_count) for item in student_summary] == [
        ("数组", 1, 1),
        ("循环", 1, 1),
    ]

    class_hotspots = list_teacher_consultation_hotspots(isolated_db, class_name="Class A", limit=5)
    assert [(item.node_name, item.mention_count, item.student_count) for item in class_hotspots] == [
        ("循环", 2, 2),
        ("数组", 1, 1),
    ]

    all_hotspots = list_teacher_consultation_hotspots(isolated_db, limit=5)
    assert [(item.node_name, item.mention_count, item.student_count) for item in all_hotspots] == [
        ("数组", 2, 2),
        ("循环", 2, 2),
    ]
