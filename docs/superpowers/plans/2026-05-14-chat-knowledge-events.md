# Chat Knowledge Events Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make chat answers stream without graph retrieval, then asynchronously record per-turn consultation knowledge points for student review and teacher analytics.

**Architecture:** Keep normal chat in `backend/services/chat_service.py`, move post-answer knowledge extraction into a focused `backend/services/chat_knowledge_event_service.py`, and expose read-only consultation summaries through existing chat/teacher API patterns. The graph remains the source of formal knowledge nodes through the mirrored `knowledge_nodes` table; chat events only reference existing nodes and never change weak-point state.

**Tech Stack:** FastAPI, SQLAlchemy ORM, MySQL-compatible schema bootstrap, OpenAI SDK, Vue 3, Axios/fetch, pytest integration tests.

---

## File Structure

- Modify: `backend/models/chat.py`
  - Add `ChatKnowledgeEvent`, relationships from `ChatSession` and `ChatMessage`.
- Modify: `backend/db/base.py`
  - Import the updated chat model so `Base.metadata.create_all()` includes the new table.
- Modify: `backend/db/bootstrap.py`
  - Add `_ensure_chat_knowledge_events_table(engine)` for existing databases.
- Create: `backend/services/chat_knowledge_event_service.py`
  - Extract candidates from one completed chat turn, match them to `KnowledgeNode`, insert idempotent events, and provide student/teacher summary queries.
- Modify: `backend/services/chat_service.py`
  - Remove blocking graph retrieval from `stream_message`.
  - Stream direct LLM answers.
  - Schedule post-response event extraction after `assistant_done` without awaiting it.
- Modify: `backend/schemas/chat.py`
  - Add consultation response schemas.
- Modify: `backend/api/routes/chat.py`
  - Add student endpoints for recent consultation events.
- Modify: `backend/schemas/teacher.py`
  - Add teacher consultation hotspot schemas.
- Modify: `backend/api/routes/teacher.py`
  - Add teacher endpoints for class hotspots and per-student consultation summaries.
- Modify: `frontend/src/api/chat.js`
  - Add student consultation API calls.
- Modify: `frontend/src/api/teacher.js`
  - Add teacher consultation API calls.
- Modify: `frontend/src/pages/ChatPage.vue`
  - Remove selected-path/retrieval UI and update copy.
- Modify: `frontend/src/pages/WeakPointsPage.vue`
  - Add a separate recent consultation section; update empty copy so chat no longer claims to create weak points.
- Modify: `frontend/src/pages/TeacherStudentsPage.vue`
  - Show consultation hotspots separately from weak points.
- Test: `tests/test_chat_knowledge_events.py`
  - Cover backend event insertion, no weak-state mutation, idempotency, and summaries.

---

### Task 1: Add Chat Knowledge Event Persistence

**Files:**
- Modify: `backend/models/chat.py`
- Modify: `backend/db/base.py`
- Modify: `backend/db/bootstrap.py`
- Test: `tests/test_chat_knowledge_events.py`

- [ ] **Step 1: Write failing model/bootstrap tests**

Create `tests/test_chat_knowledge_events.py` with:

```python
from sqlalchemy import inspect

from backend.db.session import engine
from backend.models.chat import ChatKnowledgeEvent


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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
pytest tests/test_chat_knowledge_events.py::test_chat_knowledge_event_model_has_expected_columns -v
```

Expected: FAIL with `ImportError` or missing `ChatKnowledgeEvent`.

- [ ] **Step 3: Add the ORM model**

In `backend/models/chat.py`, update imports:

```python
from sqlalchemy import DateTime, Float, ForeignKey, Text, UniqueConstraint, func
```

Add relationships:

```python
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    knowledge_events = relationship("ChatKnowledgeEvent", back_populates="session", cascade="all, delete-orphan")
```

Update `ChatMessage`:

```python
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    keywords_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    facts_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    reasoning_trace_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    retrieval_trace_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")
    consultation_events_as_user = relationship(
        "ChatKnowledgeEvent",
        foreign_keys="ChatKnowledgeEvent.user_message_id",
        back_populates="user_message",
        cascade="all, delete-orphan",
    )
    consultation_events_as_assistant = relationship(
        "ChatKnowledgeEvent",
        foreign_keys="ChatKnowledgeEvent.assistant_message_id",
        back_populates="assistant_message",
        cascade="all, delete-orphan",
    )
```

Add the new model below `ChatMessage`:

```python
class ChatKnowledgeEvent(Base):
    __tablename__ = "chat_knowledge_events"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "session_id",
            "user_message_id",
            "assistant_message_id",
            "knowledge_node_id",
            name="uq_chat_knowledge_event_turn_node",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    user_message_id: Mapped[int] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True)
    assistant_message_id: Mapped[int] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True)
    knowledge_node_id: Mapped[int] = mapped_column(ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session = relationship("ChatSession", back_populates="knowledge_events")
    user_message = relationship(
        "ChatMessage",
        foreign_keys=[user_message_id],
        back_populates="consultation_events_as_user",
    )
    assistant_message = relationship(
        "ChatMessage",
        foreign_keys=[assistant_message_id],
        back_populates="consultation_events_as_assistant",
    )
    knowledge_node = relationship("KnowledgeNode")
```

- [ ] **Step 4: Ensure metadata imports the model**

In `backend/db/base.py`, keep the existing import style:

```python
from backend.models import assignment, chat, knowledge, knowledge_state, user

__all__ = ["assignment", "chat", "knowledge", "knowledge_state", "user"]
```

No code change is needed if this already matches; verify it still imports `chat`.

- [ ] **Step 5: Add schema bootstrap for existing databases**

In `backend/db/bootstrap.py`, call the new helper in `ensure_schema_and_seed` after `_ensure_assignment_graph_linkage(engine)`:

```python
def ensure_schema_and_seed(engine: Engine) -> None:
    _ensure_user_role_column(engine)
    _ensure_user_class_column(engine)
    _ensure_knowledge_node_columns(engine)
    _ensure_assignment_submission_timing_columns(engine)
    _ensure_assignment_grading_columns(engine)
    _ensure_assignment_type_and_bank_columns(engine)
    _ensure_assignment_graph_linkage(engine)
    _ensure_chat_knowledge_events_table(engine)
    _ensure_teacher_seed(engine)
    _ensure_student_class_seed(engine)
```

Add:

```python
def _ensure_chat_knowledge_events_table(engine: Engine) -> None:
    inspector = inspect(engine)
    try:
        table_names = set(inspector.get_table_names())
    except Exception:
        return

    if "chat_knowledge_events" in table_names:
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE chat_knowledge_events (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    session_id INTEGER NOT NULL,
                    user_message_id INTEGER NOT NULL,
                    assistant_message_id INTEGER NOT NULL,
                    knowledge_node_id INTEGER NOT NULL,
                    confidence FLOAT NULL,
                    evidence_text TEXT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_chat_knowledge_event_turn_node UNIQUE (
                        user_id,
                        session_id,
                        user_message_id,
                        assistant_message_id,
                        knowledge_node_id
                    )
                )
                """
            )
        )
        connection.execute(text("CREATE INDEX ix_chat_knowledge_events_user_id ON chat_knowledge_events (user_id)"))
        connection.execute(text("CREATE INDEX ix_chat_knowledge_events_session_id ON chat_knowledge_events (session_id)"))
        connection.execute(text("CREATE INDEX ix_chat_knowledge_events_user_message_id ON chat_knowledge_events (user_message_id)"))
        connection.execute(text("CREATE INDEX ix_chat_knowledge_events_assistant_message_id ON chat_knowledge_events (assistant_message_id)"))
        connection.execute(text("CREATE INDEX ix_chat_knowledge_events_knowledge_node_id ON chat_knowledge_events (knowledge_node_id)"))
```

- [ ] **Step 6: Run persistence tests**

Run:

```powershell
pytest tests/test_chat_knowledge_events.py::test_chat_knowledge_event_model_has_expected_columns -v
pytest tests/test_chat_knowledge_events.py::test_chat_knowledge_events_table_exists_after_bootstrap -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add backend/models/chat.py backend/db/base.py backend/db/bootstrap.py tests/test_chat_knowledge_events.py
git commit -m "feat(chat): add consultation knowledge event model"
```

---

### Task 2: Build Event Extraction and Summary Service

**Files:**
- Create: `backend/services/chat_knowledge_event_service.py`
- Modify: `tests/test_chat_knowledge_events.py`

- [ ] **Step 1: Write failing service tests**

Append these tests to `tests/test_chat_knowledge_events.py`:

```python
from backend.db.session import SessionLocal
from backend.models.chat import ChatKnowledgeEvent, ChatMessage, ChatSession
from backend.models.knowledge import KnowledgeNode, UserWeakPoint
from backend.models.knowledge_state import UserKnowledgeState
from backend.models.user import User
from backend.services.chat_knowledge_event_service import (
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


def _create_chat_turn(db, prefix):
    user = User(username=f"{prefix}_student", password_hash="x", role="student", class_name="软件1班")
    node = KnowledgeNode(node_name=f"{prefix}_ArrayList", node_type="concept", chapter="集合")
    session = ChatSession(user=user, title="集合问题")
    user_message = ChatMessage(session=session, role="user", content="ArrayList 为什么越界？")
    assistant_message = ChatMessage(session=session, role="assistant", content="你访问了不存在的下标。")
    db.add_all([user, node, session, user_message, assistant_message])
    db.commit()
    return user, node, session, user_message, assistant_message


def test_extract_candidates_from_turn_parses_json():
    client = FakeClient('[{"name":"ArrayList","confidence":0.91,"evidence":"用户询问 ArrayList"}]')

    candidates = extract_candidates_from_turn(
        client,
        user_content="ArrayList 为什么越界？",
        assistant_content="访问下标超出范围。",
        previous_context=[],
    )

    assert candidates == [{"name": "ArrayList", "confidence": 0.91, "evidence": "用户询问 ArrayList"}]


def test_record_turn_knowledge_events_only_writes_existing_nodes(auto_test_prefix):
    with SessionLocal() as db:
        user, node, session, user_message, assistant_message = _create_chat_turn(db, f"{auto_test_prefix}chat_event")
        client = FakeClient(
            f'''
            [
              {{"name":"{node.node_name}","confidence":0.93,"evidence":"提到了 ArrayList"}},
              {{"name":"不存在的知识点","confidence":0.99,"evidence":"不应创建新节点"}}
            ]
            '''
        )

        inserted = record_turn_knowledge_events(
            db,
            client,
            user=user,
            session=session,
            user_message=user_message,
            assistant_message=assistant_message,
            previous_context=[],
        )
        db.commit()

        events = db.query(ChatKnowledgeEvent).filter(ChatKnowledgeEvent.user_id == user.id).all()
        assert inserted == [node.node_name]
        assert len(events) == 1
        assert events[0].knowledge_node_id == node.id
        assert db.query(KnowledgeNode).filter(KnowledgeNode.node_name == "不存在的知识点").first() is None
        assert db.query(UserWeakPoint).filter(UserWeakPoint.user_id == user.id).count() == 0
        assert db.query(UserKnowledgeState).filter(UserKnowledgeState.user_id == user.id).count() == 0


def test_record_turn_knowledge_events_is_idempotent(auto_test_prefix):
    with SessionLocal() as db:
        user, node, session, user_message, assistant_message = _create_chat_turn(db, f"{auto_test_prefix}chat_idem")
        client = FakeClient(f'[{{"name":"{node.node_name}","confidence":0.88,"evidence":"重复提及"}}]')

        first = record_turn_knowledge_events(db, client, user, session, user_message, assistant_message, [])
        second = record_turn_knowledge_events(db, client, user, session, user_message, assistant_message, [])
        db.commit()

        count = db.query(ChatKnowledgeEvent).filter(ChatKnowledgeEvent.user_id == user.id).count()
        assert first == [node.node_name]
        assert second == []
        assert count == 1


def test_consultation_summaries_group_events(auto_test_prefix):
    with SessionLocal() as db:
        user, node, session, user_message, assistant_message = _create_chat_turn(db, f"{auto_test_prefix}chat_summary")
        event = ChatKnowledgeEvent(
            user_id=user.id,
            session_id=session.id,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
            knowledge_node_id=node.id,
            confidence=0.9,
            evidence_text="集合问题",
        )
        db.add(event)
        db.commit()

        recent = list_recent_consultations(db, user, limit=10)
        student_rows = list_student_consultations(db, user.id, limit=10)
        hotspots = list_teacher_consultation_hotspots(db, class_name="软件1班", limit=10)

        assert recent[0].node_name == node.node_name
        assert student_rows[0].mention_count == 1
        assert hotspots[0].student_count == 1
```

- [ ] **Step 2: Run service tests to verify they fail**

Run:

```powershell
pytest tests/test_chat_knowledge_events.py -v
```

Expected: FAIL with missing `backend.services.chat_knowledge_event_service`.

- [ ] **Step 3: Implement candidate extraction**

Create `backend/services/chat_knowledge_event_service.py`:

```python
import json
from dataclasses import dataclass
from datetime import datetime

from openai import OpenAI
from sqlalchemy import desc, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.chat import ChatKnowledgeEvent, ChatMessage, ChatSession
from backend.models.knowledge import KnowledgeNode
from backend.models.user import User


@dataclass(frozen=True)
class ConsultationSummary:
    knowledge_node_id: int
    node_name: str
    mention_count: int
    student_count: int
    last_seen_at: datetime
    latest_session_id: int | None = None
    latest_session_title: str | None = None


@dataclass(frozen=True)
class ConsultationEventSummary:
    id: int
    knowledge_node_id: int
    node_name: str
    confidence: float | None
    evidence_text: str | None
    session_id: int
    session_title: str
    created_at: datetime


def extract_candidates_from_turn(
    client: OpenAI,
    *,
    user_content: str,
    assistant_content: str,
    previous_context: list[dict] | None = None,
) -> list[dict]:
    context_text = "\n".join(
        f"{item.get('role', '')}: {item.get('content', '')[:300]}"
        for item in (previous_context or [])[-2:]
    ) or "无"
    prompt = f"""
请从这一轮 Java 编程辅导对话中抽取涉及的正式知识点候选。

要求：
1. 只抽 Java 编程知识点。
2. 最多返回 5 个。
3. 不要返回“代码”“错误”“编程”“问题”“学习”等泛泛词。
4. 不要判断学生是否薄弱。
5. 只返回 JSON 数组，每项包含 name、confidence、evidence。

上一轮少量上下文：
{context_text}

学生消息：
{user_content}

助手回答：
{assistant_content}
"""
    response = client.chat.completions.create(
        model=settings.llm_model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    content = response.choices[0].message.content or "[]"
    return _parse_candidate_json(content)


def _parse_candidate_json(content: str) -> list[dict]:
    start = content.find("[")
    end = content.rfind("]")
    if start < 0 or end < start:
        return []
    try:
        raw_items = json.loads(content[start : end + 1])
    except json.JSONDecodeError:
        return []

    candidates: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        try:
            confidence = float(item.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        candidates.append(
            {
                "name": name,
                "confidence": max(0.0, min(confidence, 1.0)),
                "evidence": str(item.get("evidence") or "").strip()[:500],
            }
        )
        if len(candidates) >= 5:
            break
    return candidates
```

- [ ] **Step 4: Implement idempotent event recording**

Append:

```python
def record_turn_knowledge_events(
    db: Session,
    client: OpenAI,
    user: User,
    session: ChatSession,
    user_message: ChatMessage,
    assistant_message: ChatMessage,
    previous_context: list[dict] | None = None,
) -> list[str]:
    candidates = extract_candidates_from_turn(
        client,
        user_content=user_message.content,
        assistant_content=assistant_message.content,
        previous_context=previous_context or [],
    )
    if not candidates:
        return []

    candidate_names = [item["name"] for item in candidates]
    nodes = (
        db.query(KnowledgeNode)
        .filter(KnowledgeNode.node_name.in_(candidate_names))
        .all()
    )
    node_by_name = {node.node_name: node for node in nodes}

    inserted: list[str] = []
    for candidate in candidates:
        node = node_by_name.get(candidate["name"])
        if not node:
            continue
        exists = (
            db.query(ChatKnowledgeEvent)
            .filter(
                ChatKnowledgeEvent.user_id == user.id,
                ChatKnowledgeEvent.session_id == session.id,
                ChatKnowledgeEvent.user_message_id == user_message.id,
                ChatKnowledgeEvent.assistant_message_id == assistant_message.id,
                ChatKnowledgeEvent.knowledge_node_id == node.id,
            )
            .first()
        )
        if exists:
            continue
        db.add(
            ChatKnowledgeEvent(
                user_id=user.id,
                session_id=session.id,
                user_message_id=user_message.id,
                assistant_message_id=assistant_message.id,
                knowledge_node_id=node.id,
                confidence=candidate["confidence"],
                evidence_text=candidate["evidence"],
            )
        )
        inserted.append(node.node_name)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return []
    return inserted
```

- [ ] **Step 5: Implement summary queries**

Append:

```python
def list_recent_consultations(db: Session, user: User, limit: int = 20) -> list[ConsultationEventSummary]:
    rows = (
        db.query(ChatKnowledgeEvent, KnowledgeNode, ChatSession)
        .join(KnowledgeNode, ChatKnowledgeEvent.knowledge_node_id == KnowledgeNode.id)
        .join(ChatSession, ChatKnowledgeEvent.session_id == ChatSession.id)
        .filter(ChatKnowledgeEvent.user_id == user.id)
        .order_by(ChatKnowledgeEvent.created_at.desc(), ChatKnowledgeEvent.id.desc())
        .limit(limit)
        .all()
    )
    return [
        ConsultationEventSummary(
            id=event.id,
            knowledge_node_id=node.id,
            node_name=node.node_name,
            confidence=event.confidence,
            evidence_text=event.evidence_text,
            session_id=session.id,
            session_title=session.title,
            created_at=event.created_at,
        )
        for event, node, session in rows
    ]


def list_student_consultations(db: Session, student_id: int, limit: int = 20) -> list[ConsultationSummary]:
    rows = (
        db.query(
            KnowledgeNode.id.label("knowledge_node_id"),
            KnowledgeNode.node_name.label("node_name"),
            func.count(ChatKnowledgeEvent.id).label("mention_count"),
            func.count(func.distinct(ChatKnowledgeEvent.user_id)).label("student_count"),
            func.max(ChatKnowledgeEvent.created_at).label("last_seen_at"),
        )
        .join(ChatKnowledgeEvent, ChatKnowledgeEvent.knowledge_node_id == KnowledgeNode.id)
        .filter(ChatKnowledgeEvent.user_id == student_id)
        .group_by(KnowledgeNode.id, KnowledgeNode.node_name)
        .order_by(desc("last_seen_at"))
        .limit(limit)
        .all()
    )
    return [
        ConsultationSummary(
            knowledge_node_id=row.knowledge_node_id,
            node_name=row.node_name,
            mention_count=int(row.mention_count or 0),
            student_count=int(row.student_count or 0),
            last_seen_at=row.last_seen_at,
        )
        for row in rows
    ]


def list_teacher_consultation_hotspots(
    db: Session,
    *,
    class_name: str | None = None,
    limit: int = 10,
) -> list[ConsultationSummary]:
    query = (
        db.query(
            KnowledgeNode.id.label("knowledge_node_id"),
            KnowledgeNode.node_name.label("node_name"),
            func.count(ChatKnowledgeEvent.id).label("mention_count"),
            func.count(func.distinct(ChatKnowledgeEvent.user_id)).label("student_count"),
            func.max(ChatKnowledgeEvent.created_at).label("last_seen_at"),
        )
        .join(ChatKnowledgeEvent, ChatKnowledgeEvent.knowledge_node_id == KnowledgeNode.id)
        .join(User, ChatKnowledgeEvent.user_id == User.id)
    )
    if class_name:
        query = query.filter(User.class_name == class_name)
    rows = (
        query.group_by(KnowledgeNode.id, KnowledgeNode.node_name)
        .order_by(desc("student_count"), desc("mention_count"), desc("last_seen_at"))
        .limit(limit)
        .all()
    )
    return [
        ConsultationSummary(
            knowledge_node_id=row.knowledge_node_id,
            node_name=row.node_name,
            mention_count=int(row.mention_count or 0),
            student_count=int(row.student_count or 0),
            last_seen_at=row.last_seen_at,
        )
        for row in rows
    ]
```

- [ ] **Step 6: Run service tests**

Run:

```powershell
pytest tests/test_chat_knowledge_events.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add backend/services/chat_knowledge_event_service.py tests/test_chat_knowledge_events.py
git commit -m "feat(chat): record consultation knowledge events"
```

---

### Task 3: Make Chat Stream Without Blocking Graph Retrieval

**Files:**
- Modify: `backend/services/chat_service.py`
- Modify: `backend/api/routes/chat.py`
- Modify: `tests/test_chat_knowledge_events.py`

- [ ] **Step 1: Write failing direct-chat test**

Append:

```python
from backend.schemas.chat import MessageCreateRequest
from backend.services import chat_service


def test_stream_message_does_not_call_graph_retrieval(monkeypatch, auto_test_prefix):
    with SessionLocal() as db:
        user = User(username=f"{auto_test_prefix}direct_chat", password_hash="x", role="student")
        session = ChatSession(user=user, title="新对话")
        db.add_all([user, session])
        db.commit()

        def fail_graph_call(*args, **kwargs):
            raise AssertionError("graph retrieval should not run before chat answer")

        class StreamingCompletions:
            def create(self, **kwargs):
                if kwargs.get("stream"):
                    delta = type("Delta", (), {"content": "直接回答"})()
                    choice = type("Choice", (), {"delta": delta})()
                    return [type("Chunk", (), {"choices": [choice]})()]
                message = type("Message", (), {"content": "测试标题"})()
                return type("Resp", (), {"choices": [type("Choice", (), {"message": message})()]})()

        fake_client = type("Client", (), {"chat": type("Chat", (), {"completions": StreamingCompletions()})()})()

        monkeypatch.setattr(chat_service, "get_openai_client", lambda: fake_client)
        monkeypatch.setattr(chat_service.rag_engine, "query_graph_with_reasoning", fail_graph_call)
        monkeypatch.setattr(chat_service.rag_engine, "extract_keywords_with_llm", fail_graph_call)
        monkeypatch.setattr(chat_service, "_schedule_turn_knowledge_extraction", lambda *args, **kwargs: None)

        events = list(chat_service.stream_message(db, user, session.id, MessageCreateRequest(content="解释 ArrayList")))

        assert any("assistant_delta" in event for event in events)
        assert any("assistant_done" in event for event in events)
```

- [ ] **Step 2: Run direct-chat test to verify it fails**

Run:

```powershell
pytest tests/test_chat_knowledge_events.py::test_stream_message_does_not_call_graph_retrieval -v
```

Expected: FAIL because current `stream_message` calls graph retrieval.

- [ ] **Step 3: Add direct answer streaming helper**

In `backend/services/chat_service.py`, remove unused imports after refactor:

```python
from backend.services import rag_engine
from backend.services.weak_point_service import extract_core_nodes, upsert_weak_points
```

Replace with:

```python
from backend.db.session import SessionLocal
from backend.services.chat_knowledge_event_service import record_turn_knowledge_events
```

Add:

```python
def _stream_direct_tutor_answer(client: OpenAI, user_input: str, history: list[dict]):
    system_prompt = """
你是一名 Java 编程作业智能辅导员。

要求：
1. 优先解释学生当前问题或代码错误。
2. 用循序渐进的方式帮助学生理解原因。
3. 可以给出关键代码片段，但不要替学生完成整份作业。
4. 如果信息不足，先指出最可能的原因并提出一个可验证的检查点。
"""
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend({"role": item["role"], "content": item["content"]} for item in history[-6:])
    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model=settings.llm_model_name,
        messages=messages,
        stream=True,
        temperature=0.2,
    )
    for chunk in response:
        content = chunk.choices[0].delta.content
        if content:
            yield content
```

- [ ] **Step 4: Replace `stream_message` graph path**

Rewrite the body after `history`:

```python
    history = _build_history(db, session.id, exclude_message_id=user_message.id)
    client = get_openai_client()
    should_autogenerate_title = _should_autogenerate_title(session, history)

    db.flush()
    yield _sse_event("user_message", _message_to_schema(user_message).model_dump(mode="json"))

    answer_started_at = perf_counter()
    chunks: list[str] = []
    for chunk in _stream_direct_tutor_answer(client, payload.content, history=history):
        chunks.append(chunk)
        yield _sse_event("assistant_delta", {"content": chunk})
    answer = "".join(chunks)
    answer_elapsed = perf_counter() - answer_started_at

    assistant_message = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer,
        keywords_json=[],
        facts_json=[],
        reasoning_trace_json=[],
        retrieval_trace_json=[],
    )
    db.add(assistant_message)

    if should_autogenerate_title:
        session.title = _generate_session_title(client, payload.content, answer)

    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)

    assistant_schema = _message_to_schema(assistant_message)

    print(
        "[chat_timing] "
        f"session={session.id} "
        f"answer={answer_elapsed:.2f}s "
        f"total={perf_counter() - request_started_at:.2f}s"
    )

    yield _sse_event(
        "assistant_done",
        {
            "assistant_message": assistant_schema.model_dump(mode="json"),
            "weak_points_added": [],
        },
    )

    _schedule_turn_knowledge_extraction(
        user_id=user.id,
        session_id=session.id,
        user_message_id=user_message.id,
        assistant_message_id=assistant_message.id,
        previous_context=history[-2:],
    )
```

- [ ] **Step 5: Add non-blocking extraction scheduler**

At top of `chat_service.py` add:

```python
from threading import Thread
```

Add below `stream_message`:

```python
def _schedule_turn_knowledge_extraction(
    *,
    user_id: int,
    session_id: int,
    user_message_id: int,
    assistant_message_id: int,
    previous_context: list[dict],
) -> None:
    thread = Thread(
        target=_run_turn_knowledge_extraction,
        kwargs={
            "user_id": user_id,
            "session_id": session_id,
            "user_message_id": user_message_id,
            "assistant_message_id": assistant_message_id,
            "previous_context": previous_context,
        },
        daemon=True,
    )
    thread.start()


def _run_turn_knowledge_extraction(
    *,
    user_id: int,
    session_id: int,
    user_message_id: int,
    assistant_message_id: int,
    previous_context: list[dict],
) -> None:
    with SessionLocal() as task_db:
        try:
            user = task_db.query(User).filter(User.id == user_id).first()
            session = task_db.query(ChatSession).filter(ChatSession.id == session_id).first()
            user_message = task_db.query(ChatMessage).filter(ChatMessage.id == user_message_id).first()
            assistant_message = task_db.query(ChatMessage).filter(ChatMessage.id == assistant_message_id).first()
            if not user or not session or not user_message or not assistant_message:
                return
            inserted = record_turn_knowledge_events(
                task_db,
                get_openai_client(),
                user,
                session,
                user_message,
                assistant_message,
                previous_context,
            )
            task_db.commit()
            if inserted:
                print(f"[chat_knowledge_events] session={session_id} nodes={inserted}")
        except Exception as error:
            task_db.rollback()
            print(f"[chat_knowledge_events] extraction failed: {error}")
```

- [ ] **Step 6: Run direct-chat test**

Run:

```powershell
pytest tests/test_chat_knowledge_events.py::test_stream_message_does_not_call_graph_retrieval -v
```

Expected: PASS.

- [ ] **Step 7: Run syntax check**

Run:

```powershell
python -m compileall backend
```

Expected: no compile errors.

- [ ] **Step 8: Commit**

```powershell
git add backend/services/chat_service.py tests/test_chat_knowledge_events.py
git commit -m "feat(chat): stream answers without graph retrieval"
```

---

### Task 4: Add Student and Teacher Consultation APIs

**Files:**
- Modify: `backend/schemas/chat.py`
- Modify: `backend/api/routes/chat.py`
- Modify: `backend/schemas/teacher.py`
- Modify: `backend/api/routes/teacher.py`
- Modify: `tests/test_chat_knowledge_events.py`

- [ ] **Step 1: Add schema classes**

In `backend/schemas/chat.py`, append:

```python
class ChatConsultationEventResponse(BaseModel):
    id: int
    knowledge_node_id: int
    node_name: str
    confidence: float | None = None
    evidence_text: str | None = None
    session_id: int
    session_title: str
    created_at: datetime
```

In `backend/schemas/teacher.py`, append:

```python
class TeacherConsultationSummaryResponse(BaseModel):
    knowledge_node_id: int
    node_name: str
    mention_count: int
    student_count: int
    last_seen_at: datetime
```

- [ ] **Step 2: Add student route**

In `backend/api/routes/chat.py`, import:

```python
from backend.schemas.chat import ChatConsultationEventResponse, MessageCreateRequest, SessionCreateRequest, SessionUpdateRequest
from backend.services.chat_knowledge_event_service import list_recent_consultations
```

Add route:

```python
@router.get("/consultations/recent", response_model=list[ChatConsultationEventResponse])
def get_recent_consultations(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = list_recent_consultations(db, current_user, limit=max(1, min(limit, 50)))
    return [ChatConsultationEventResponse(**row.__dict__) for row in rows]
```

- [ ] **Step 3: Add teacher routes**

In `backend/api/routes/teacher.py`, import:

```python
from backend.schemas.teacher import TeacherConsultationSummaryResponse
from backend.services.chat_knowledge_event_service import (
    list_student_consultations,
    list_teacher_consultation_hotspots,
)
```

Add routes:

```python
@router.get("/consultations/hotspots", response_model=list[TeacherConsultationSummaryResponse])
def get_consultation_hotspots(
    class_name: str | None = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    rows = list_teacher_consultation_hotspots(db, class_name=class_name, limit=max(1, min(limit, 50)))
    return [TeacherConsultationSummaryResponse(**row.__dict__) for row in rows]


@router.get("/students/{student_id}/consultations", response_model=list[TeacherConsultationSummaryResponse])
def get_student_consultations(
    student_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    rows = list_student_consultations(db, student_id, limit=max(1, min(limit, 50)))
    return [TeacherConsultationSummaryResponse(**row.__dict__) for row in rows]
```

Use the existing `get_current_teacher` dependency already imported by `backend/api/routes/teacher.py`.

- [ ] **Step 4: Write route import test**

Append to `tests/test_chat_knowledge_events.py`:

```python
def test_chat_and_teacher_consultation_routes_are_registered():
    from backend.main import app

    paths = {route.path for route in app.routes}

    assert "/api/chat/consultations/recent" in paths
    assert "/api/teacher/consultations/hotspots" in paths
    assert "/api/teacher/students/{student_id}/consultations" in paths
```

- [ ] **Step 5: Run API route test**

Run:

```powershell
pytest tests/test_chat_knowledge_events.py::test_chat_and_teacher_consultation_routes_are_registered -v
```

Expected: PASS.

- [ ] **Step 6: Run backend compile**

Run:

```powershell
python -m compileall backend
```

Expected: no compile errors.

- [ ] **Step 7: Commit**

```powershell
git add backend/schemas/chat.py backend/api/routes/chat.py backend/schemas/teacher.py backend/api/routes/teacher.py tests/test_chat_knowledge_events.py
git commit -m "feat(chat): expose consultation analytics APIs"
```

---

### Task 5: Update ChatPage UI and API Clients

**Files:**
- Modify: `frontend/src/api/chat.js`
- Modify: `frontend/src/pages/ChatPage.vue`

- [ ] **Step 1: Add frontend API method**

In `frontend/src/api/chat.js`, add:

```javascript
export const listRecentConsultationsApi = (limit = 20) =>
  http.get("/api/chat/consultations/recent", { params: { limit } });
```

- [ ] **Step 2: Remove selected path UI from ChatPage**

In `frontend/src/pages/ChatPage.vue`, remove:

```vue
<SelectedPathGraph v-if="message.role === 'assistant'" :facts="message.facts || []" />
```

Remove the `<details class="trace-box">...</details>` block that displays `reasoning_trace` and `retrieval_trace`.

Remove:

```javascript
import SelectedPathGraph from "../components/SelectedPathGraph.vue";
```

Change topbar copy:

```vue
<p>AI 编程作业辅导</p>
```

- [ ] **Step 3: Keep response compatibility**

Leave the temporary message shape fields as empty arrays so existing API responses still render safely:

```javascript
facts: [],
reasoning_trace: [],
retrieval_trace: [],
```

- [ ] **Step 4: Build frontend**

Run:

```powershell
npm --prefix frontend run build
```

Expected: build succeeds.

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/api/chat.js frontend/src/pages/ChatPage.vue
git commit -m "feat(chat): simplify tutoring UI after graph decoupling"
```

---

### Task 6: Add Student Recent Consultation View

**Files:**
- Modify: `frontend/src/pages/WeakPointsPage.vue`

- [ ] **Step 1: Add API import and state**

In `WeakPointsPage.vue`, add:

```javascript
import { listRecentConsultationsApi } from "../api/chat";
```

Add state near existing refs:

```javascript
const recentConsultations = ref([]);
```

- [ ] **Step 2: Load consultation events on mount**

In `onMounted`, start the request beside history:

```javascript
const consultationPromise = loadRecentConsultations();
```

Include it in settled promises:

```javascript
await Promise.allSettled([historyPromise, graphPromise, consultationPromise]);
```

Add function:

```javascript
async function loadRecentConsultations() {
  try {
    const { data } = await listRecentConsultationsApi(12);
    recentConsultations.value = data || [];
  } catch (error) {
    handleApiError(error, "加载最近提问记录失败。");
  }
}
```

- [ ] **Step 3: Add separate recent consultation section**

Add this section after the summary row and before the graph layout:

```vue
<section v-if="recentConsultations.length" class="panel consultation-section">
  <div class="history-header">
    <h2>最近提问知识点</h2>
    <p>这些来自聊天问答记录，只表示你最近关注过，不会自动计入薄弱点。</p>
  </div>
  <div class="history-grid">
    <article v-for="item in recentConsultations" :key="item.id" class="history-card consultation-card">
      <div class="history-card-top">
        <span class="history-badge">提问</span>
        <span class="history-time">{{ formatDate(item.created_at) }}</span>
      </div>
      <h3>{{ item.node_name }}</h3>
      <span class="weak-first-seen">{{ item.session_title || "聊天记录" }}</span>
      <router-link class="consultation-link" to="/chat">回到聊天</router-link>
    </article>
  </div>
</section>
```

- [ ] **Step 4: Fix weak-point empty copy**

Replace:

```vue
<div v-else-if="!graphNodes.length" class="graph-state">当前没有可展示的知识图谱节点，请先完成作业或在聊天页面提问以记录薄弱点。</div>
```

with:

```vue
<div v-else-if="!graphNodes.length" class="graph-state">当前没有可展示的薄弱点图谱，请先完成作业或训练来记录待掌握知识点。</div>
```

Replace:

```vue
<p>继续提问时，系统会在选出解释路径后，自动记录少量最关键的知识节点。</p>
```

with:

```vue
<p>聊天会记录最近提问过的知识点；作业和训练结果会记录真正需要攻克的薄弱点。</p>
```

- [ ] **Step 5: Add scoped CSS**

Append:

```css
.consultation-section {
  display: grid;
  gap: 12px;
}

.consultation-card {
  border-color: #dbeafe;
}

.consultation-link {
  color: var(--app-primary);
  text-decoration: none;
  font-size: var(--compact-caption);
}
```

- [ ] **Step 6: Build frontend**

Run:

```powershell
npm --prefix frontend run build
```

Expected: build succeeds.

- [ ] **Step 7: Commit**

```powershell
git add frontend/src/pages/WeakPointsPage.vue
git commit -m "feat(student): show recent chat consultation points"
```

---

### Task 7: Add Teacher Consultation Hotspots

**Files:**
- Modify: `frontend/src/api/teacher.js`
- Modify: `frontend/src/pages/TeacherStudentsPage.vue`

- [ ] **Step 1: Add teacher API methods**

In `frontend/src/api/teacher.js`, add:

```javascript
export const listTeacherConsultationHotspotsApi = (params = {}) =>
  http.get("/api/teacher/consultations/hotspots", { params });

export const listTeacherStudentConsultationsApi = (studentId, limit = 20) =>
  http.get(`/api/teacher/students/${studentId}/consultations`, { params: { limit } });
```

- [ ] **Step 2: Import and add state in TeacherStudentsPage**

Change import:

```javascript
import {
  listTeacherConsultationHotspotsApi,
  listTeacherStudentConsultationsApi,
  listTeacherStudentWeakPointsApi,
  listTeacherStudentsApi,
} from "../api/teacher";
```

Add refs:

```javascript
const consultationHotspots = ref([]);
const studentConsultations = ref([]);
```

- [ ] **Step 3: Load class hotspots**

In `loadStudents`, after students are loaded:

```javascript
const hotspotsResponse = await listTeacherConsultationHotspotsApi({ limit: 8 });
consultationHotspots.value = hotspotsResponse.data || [];
```

If this request fails, let existing catch show `加载学生列表失败。`; the teacher page should make the missing analytics visible during development.

- [ ] **Step 4: Load selected student consultations**

In `selectStudent`, request both weak points and consultation summaries:

```javascript
const [weakPointsResponse, consultationsResponse] = await Promise.all([
  listTeacherStudentWeakPointsApi(studentId),
  listTeacherStudentConsultationsApi(studentId, 12),
]);
if (requestId !== activeRequestId) return;
studentWeakPoints.value = weakPointsResponse.data;
studentConsultations.value = consultationsResponse.data || [];
```

Reset `studentConsultations.value = [];` when a new student is selected.

- [ ] **Step 5: Add class hotspot section**

Add above `.students-layout`:

```vue
<section v-if="consultationHotspots.length" class="detail-section hotspot-section">
  <div class="section-head">
    <h4>班级提问热点</h4>
    <span>聊天关注点，不等同薄弱点</span>
  </div>
  <div class="weak-cards">
    <article v-for="item in consultationHotspots" :key="item.knowledge_node_id" class="weak-card consultation-card">
      <strong>{{ item.node_name }}</strong>
      <span>{{ item.student_count }} 人 · {{ item.mention_count }} 次</span>
    </article>
  </div>
</section>
```

- [ ] **Step 6: Add selected student consultation section**

Add below the current weak-point detail section:

```vue
<section class="detail-section">
  <div class="section-head">
    <h4>最近提问知识点</h4>
    <span>{{ studentConsultations.length }} 个</span>
  </div>
  <div v-if="!isStudentsLoading && !isWeakPointsLoading && studentConsultations.length" class="weak-cards">
    <article v-for="item in studentConsultations" :key="item.knowledge_node_id" class="weak-card consultation-card">
      <strong>{{ item.node_name }}</strong>
      <span>{{ item.mention_count }} 次提问</span>
    </article>
  </div>
  <div v-else-if="hasStudentsLoaded" class="empty">该学生暂时没有聊天提问知识点记录。</div>
</section>
```

- [ ] **Step 7: Add CSS distinction**

Append:

```css
.hotspot-section {
  padding: 16px;
  border: 1px solid var(--app-line);
  border-radius: var(--app-radius-xl);
  background: var(--app-panel);
  box-shadow: var(--app-shadow);
}

.consultation-card {
  border-color: #dbeafe;
  background: #f8fbff;
}
```

- [ ] **Step 8: Build frontend**

Run:

```powershell
npm --prefix frontend run build
```

Expected: build succeeds.

- [ ] **Step 9: Commit**

```powershell
git add frontend/src/api/teacher.js frontend/src/pages/TeacherStudentsPage.vue
git commit -m "feat(teacher): show chat consultation hotspots"
```

---

### Task 8: Final Verification and Documentation Update

**Files:**
- Modify: `docs/teacher-graph-maintenance.md`

- [ ] **Step 1: Update graph maintenance docs**

In `docs/teacher-graph-maintenance.md`, update the data boundary section to state:

```markdown
- ChatPage 不再在回答前检索 Neo4j 图谱；聊天回答完成后会异步抽取本轮涉及的正式知识点，写入提问记录用于学生回看和教师热点统计。
- 聊天提问记录只是弱学习足迹，不会写入 `user_weak_points`，也不会改变 `user_knowledge_states`。
```

Keep the existing rule that assignment wrong submissions mark bound knowledge nodes weak.

- [ ] **Step 2: Run backend syntax check**

Run:

```powershell
python -m compileall backend
```

Expected: no compile errors.

- [ ] **Step 3: Run focused backend tests**

Run:

```powershell
pytest tests/test_chat_knowledge_events.py tests/test_assignment_weak_points.py tests/test_weak_point_flow.py -v
```

Expected: PASS. If integration services are unavailable, record the exact failing external dependency in the final handoff.

- [ ] **Step 4: Run frontend build**

Run:

```powershell
npm --prefix frontend run build
```

Expected: build succeeds.

- [ ] **Step 5: Check git diff for scope**

Run:

```powershell
git status --short
git diff --stat HEAD
```

Expected: only files from this plan are changed. Do not revert unrelated user changes such as `frontend/src/pages/TeacherAssignmentProgressPage.vue`.

- [ ] **Step 6: Commit docs and final polish**

```powershell
git add docs/teacher-graph-maintenance.md
git commit -m "docs(graph): document chat consultation event boundary"
```

---

## Implementation Notes

- Keep `MessageCreateRequest.rag_depth` and `rag_width` for request compatibility, but do not use them in the direct chat path.
- Keep `MessageResponse.facts`, `reasoning_trace`, and `retrieval_trace` for old messages and compatibility; new assistant messages should save empty arrays.
- The first implementation uses a daemon thread for background extraction because this app runs as a local FastAPI service. If production deployment needs durable jobs later, replace `_schedule_turn_knowledge_extraction` with a queue without changing the event service contract.
- Do not remove `backend/services/rag_engine.py` in this plan. Weak point graph recommendation and other old code may still reference graph utilities.
- Do not alter assignment weak-point behavior. The strong signal remains wrong submissions on teacher-bound knowledge nodes.

## Self-Review

- Spec coverage: direct chat, no pre-answer Neo4j retrieval, per-turn async extraction, existing-node-only matching, student recent consultations, teacher hotspots, no weak-state mutation, and verification are all covered by Tasks 1-8.
- Placeholder scan: this plan contains no placeholder markers and no intentionally incomplete sections.
- Type consistency: service dataclasses map to schema field names; API clients use the planned route paths; tests use the planned model and service names.
