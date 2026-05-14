import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from backend.db import base as model_base  # noqa: F401
from backend.db.bootstrap import ensure_schema_and_seed
from backend.db.bootstrap import _ensure_chat_knowledge_events_table
from backend.db.session import Base
from backend.models.chat import ChatKnowledgeEvent, ChatMessage, ChatSession
from backend.models.knowledge import KnowledgeNode, UserWeakPoint
from backend.models.knowledge_state import UserKnowledgeState
from backend.models.user import User
from backend.services.chat_knowledge_event_service import (
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
    inspector = inspect(isolated_engine)

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
        "confidence",
        "evidence_text",
        "created_at",
    }.issubset(columns)


def test_bootstrap_helper_creates_chat_knowledge_events_with_model_constraints():
    test_engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=test_engine)
    ChatKnowledgeEvent.__table__.drop(bind=test_engine)

    _ensure_chat_knowledge_events_table(test_engine)

    inspector = inspect(test_engine)
    assert "chat_knowledge_events" in inspector.get_table_names()

    columns = {column["name"] for column in inspector.get_columns("chat_knowledge_events")}
    assert {
        "id",
        "user_id",
        "session_id",
        "user_message_id",
        "assistant_message_id",
        "knowledge_node_id",
        "confidence",
        "evidence_text",
        "created_at",
    }.issubset(columns)

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


def test_extract_candidates_from_turn_parses_json_from_fake_openai_client():
    client = FakeClient(
        """
        下面是抽取结果：
        [
          {"name": "空指针异常", "confidence": 1.2, "evidence": "学生询问 NullPointerException"},
          {"name": "数组", "confidence": -0.2, "evidence": "%s"}
        ]
        """
        % ("x" * 600)
    )

    candidates = extract_candidates_from_turn(
        client,
        user_content="为什么我的对象调用方法会报 NullPointerException？",
        assistant_content="先判断对象是否为 null，再调用方法。",
        previous_context="Java 异常处理",
    )

    assert candidates == [
        {"name": "空指针异常", "confidence": 1.0, "evidence": "学生询问 NullPointerException"},
        {"name": "数组", "confidence": 0.0, "evidence": "x" * 500},
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
              {"name": "空指针异常", "confidence": 0.9, "evidence": "学生询问 NPE"},
              {"name": "不存在的概念", "confidence": 0.8, "evidence": "不应创建新节点"}
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


def test_record_turn_knowledge_events_requires_python_exact_node_name_match(isolated_db):
    user = _student(isolated_db)
    _node(isolated_db, "arraylist")
    session, user_message, assistant_message = _turn(isolated_db, user)

    inserted = record_turn_knowledge_events(
        isolated_db,
        FakeClient('[{"name": "ArrayList", "confidence": 0.9, "evidence": "大小写不同"}]'),
        user,
        session,
        user_message,
        assistant_message,
    )

    assert inserted == []
    assert isolated_db.query(ChatKnowledgeEvent).count() == 0


def test_record_turn_knowledge_events_is_idempotent_for_same_turn_and_node(isolated_db):
    user = _student(isolated_db)
    _node(isolated_db, "循环")
    session, user_message, assistant_message = _turn(isolated_db, user)
    client = FakeClient('[{"name": "循环", "confidence": 0.7, "evidence": "for 循环条件"}]')

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
                confidence=0.9,
                evidence_text="alice loops",
            ),
            ChatKnowledgeEvent(
                user_id=alice.id,
                session_id=alice_session.id,
                user_message_id=alice_user_message.id,
                assistant_message_id=alice_assistant_message.id,
                knowledge_node_id=arrays.id,
                confidence=0.8,
                evidence_text="alice arrays",
            ),
            ChatKnowledgeEvent(
                user_id=bob.id,
                session_id=bob_session.id,
                user_message_id=bob_user_message.id,
                assistant_message_id=bob_assistant_message.id,
                knowledge_node_id=loops.id,
                confidence=0.7,
                evidence_text="bob loops",
            ),
            ChatKnowledgeEvent(
                user_id=charlie.id,
                session_id=charlie_session.id,
                user_message_id=charlie_user_message.id,
                assistant_message_id=charlie_assistant_message.id,
                knowledge_node_id=arrays.id,
                confidence=0.6,
                evidence_text="charlie arrays",
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
