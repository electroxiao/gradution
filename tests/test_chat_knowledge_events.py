import pytest
from sqlalchemy import create_engine, inspect

from backend.db import base as model_base  # noqa: F401
from backend.db.bootstrap import ensure_schema_and_seed
from backend.db.bootstrap import _ensure_chat_knowledge_events_table
from backend.db.session import Base, engine
from backend.models.chat import ChatKnowledgeEvent


@pytest.fixture(scope="session", autouse=True)
def backend_ready():
    return None


@pytest.fixture(scope="session", autouse=True)
def clean_auto_test_data():
    return None


@pytest.fixture(scope="module", autouse=True)
def bootstrap_schema():
    Base.metadata.create_all(bind=engine)
    ensure_schema_and_seed(engine)


def test_chat_knowledge_events_table_exists_after_bootstrap():
    inspector = inspect(engine)

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
