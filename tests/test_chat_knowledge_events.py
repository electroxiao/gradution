import pytest
from sqlalchemy import inspect

from backend.db.bootstrap import ensure_schema_and_seed
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
