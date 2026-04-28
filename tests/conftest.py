from __future__ import annotations

import os
import time
from collections.abc import Iterator

import httpx
import pytest
from neo4j.exceptions import Neo4jError, ServiceUnavailable
from sqlalchemy import delete, select

from backend.core.config import settings
from backend.db.session import SessionLocal
from backend.models.assignment import (
    Assignment,
    AssignmentAssignee,
    AssignmentQuestion,
    AssignmentQuestionKnowledgeNode,
    AssignmentSubmission,
    AssignmentTestCase,
    QuestionBankItem,
)
from backend.models.knowledge_state import UserConceptMastery
from backend.models.user import User


DEFAULT_TIMEOUT = 60.0


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--backend-base-url",
        action="store",
        default=os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:9000"),
        help="Base URL for the running FastAPI backend.",
    )


@pytest.fixture(scope="session")
def auto_test_prefix() -> str:
    return os.getenv("AUTO_TEST_PREFIX", "AUTO_TEST_")


@pytest.fixture(scope="session")
def backend_base_url(pytestconfig: pytest.Config) -> str:
    return str(pytestconfig.getoption("--backend-base-url")).rstrip("/")


@pytest.fixture(scope="session")
def teacher_credentials() -> tuple[str, str]:
    return (
        os.getenv("TEST_TEACHER_USERNAME", "teacher"),
        os.getenv("TEST_TEACHER_PASSWORD", "teacher123"),
    )


@pytest.fixture(scope="session")
def client(backend_base_url: str) -> Iterator[httpx.Client]:
    limits = httpx.Limits(max_keepalive_connections=0, max_connections=10)
    with httpx.Client(
        base_url=backend_base_url,
        timeout=DEFAULT_TIMEOUT,
        limits=limits,
        headers={"Connection": "close"},
    ) as test_client:
        yield test_client


@pytest.fixture(scope="session", autouse=True)
def clean_auto_test_data(auto_test_prefix: str) -> Iterator[None]:
    cleanup_auto_test_data(auto_test_prefix)
    yield
    cleanup_auto_test_data(auto_test_prefix)


@pytest.fixture(scope="session", autouse=True)
def backend_ready(client: httpx.Client) -> None:
    try:
        response = client.get("/api/health", timeout=5.0)
    except httpx.RequestError as error:
        pytest.fail(
            "Backend is not responding at /api/health. "
            "Start or restart FastAPI before running the integration tests. "
            f"Original error: {error}",
            pytrace=False,
        )
    assert_status(response, 200)


def cleanup_auto_test_data(prefix: str) -> None:
    """Remove only records created by these integration tests."""
    prefix_pattern = _like_prefix_pattern(prefix)
    with SessionLocal() as db:
        assignment_ids = list(
            db.scalars(
                select(Assignment.id).where(
                    Assignment.title.like(prefix_pattern, escape="\\")
                )
            ).all()
        )
        user_ids = list(
            db.scalars(
                select(User.id).where(User.username.like(prefix_pattern, escape="\\"))
            ).all()
        )

        question_ids: list[int] = []
        submission_ids: list[int] = []
        if assignment_ids:
            question_ids = list(
                db.scalars(
                    select(AssignmentQuestion.id).where(
                        AssignmentQuestion.assignment_id.in_(assignment_ids)
                    )
                ).all()
            )
            submission_ids = list(
                db.scalars(
                    select(AssignmentSubmission.id).where(
                        AssignmentSubmission.assignment_id.in_(assignment_ids)
                    )
                ).all()
            )

        if user_ids:
            extra_submission_ids = list(
                db.scalars(
                    select(AssignmentSubmission.id).where(
                        AssignmentSubmission.student_id.in_(user_ids)
                    )
                ).all()
            )
            submission_ids = sorted({*submission_ids, *extra_submission_ids})

        if user_ids or submission_ids:
            conditions = []
            if user_ids:
                conditions.append(UserConceptMastery.student_id.in_(user_ids))
            if submission_ids:
                conditions.append(UserConceptMastery.last_source_submission_id.in_(submission_ids))
            for condition in conditions:
                db.execute(delete(UserConceptMastery).where(condition))

        if question_ids:
            db.execute(
                delete(AssignmentQuestionKnowledgeNode).where(
                    AssignmentQuestionKnowledgeNode.question_id.in_(question_ids)
                )
            )
            db.execute(
                delete(AssignmentTestCase).where(
                    AssignmentTestCase.question_id.in_(question_ids)
                )
            )

        if submission_ids:
            db.execute(
                delete(AssignmentSubmission).where(AssignmentSubmission.id.in_(submission_ids))
            )

        if assignment_ids:
            db.execute(
                delete(AssignmentAssignee).where(
                    AssignmentAssignee.assignment_id.in_(assignment_ids)
                )
            )
            db.execute(
                delete(AssignmentQuestion).where(AssignmentQuestion.assignment_id.in_(assignment_ids))
            )
            db.execute(delete(Assignment).where(Assignment.id.in_(assignment_ids)))

        db.execute(delete(QuestionBankItem).where(QuestionBankItem.title.like(prefix_pattern, escape="\\")))

        if user_ids:
            db.execute(delete(User).where(User.id.in_(user_ids)))

        db.commit()


def _like_prefix_pattern(prefix: str) -> str:
    escaped = (
        prefix.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
    return f"{escaped}%"


def assert_status(response: httpx.Response, expected: int | set[int]) -> None:
    expected_codes = {expected} if isinstance(expected, int) else expected
    assert response.status_code in expected_codes, (
        f"Expected {sorted(expected_codes)}, got {response.status_code}: {response.text}"
    )


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def unique_name(prefix: str, stem: str) -> str:
    return f"{prefix}{stem}_{int(time.time() * 1000)}"


@pytest.fixture(scope="session")
def neo4j_available() -> None:
    from backend.services.chat_service import get_neo4j_driver

    try:
        driver = get_neo4j_driver()
        with driver.session(database=settings.neo4j_db_name) as session:
            session.run("RETURN 1 AS ok").consume()
    except (Neo4jError, OSError, ServiceUnavailable) as error:
        pytest.fail(
            "Neo4j is not reachable for the real integration test. "
            f"Start Neo4j or update NEO4J_URI/NEO4J_* in .env. "
            f"Current uri={settings.neo4j_uri!r}, database={settings.neo4j_db_name!r}. "
            f"Original error: {error}",
            pytrace=False,
        )


@pytest.fixture(scope="session")
def teacher_token(client: httpx.Client, teacher_credentials: tuple[str, str]) -> str:
    username, password = teacher_credentials
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert_status(response, 200)
    data = response.json()
    assert data["user"]["role"] == "teacher"
    return data["access_token"]


@pytest.fixture(scope="session")
def test_student(client: httpx.Client, auto_test_prefix: str) -> dict:
    username = unique_name(auto_test_prefix, "student")
    password = "AutoTest123"
    response = client.post(
        "/api/auth/register",
        json={"username": username, "password": password},
    )
    assert_status(response, 200)
    data = response.json()
    assert data["user"]["username"] == username
    assert data["user"]["role"] == "student"
    return {
        "id": data["user"]["id"],
        "username": username,
        "password": password,
        "token": data["access_token"],
    }
