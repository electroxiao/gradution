from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.chat import ChatKnowledgeEvent, ChatMessage, ChatSession
from backend.models.knowledge import KnowledgeNode
from backend.models.user import User


@dataclass(frozen=True)
class ConsultationEventSummary:
    event_id: int
    session_id: int
    session_title: str
    user_message_id: int
    assistant_message_id: int
    node_id: int
    node_name: str
    confidence: float | None
    evidence_text: str | None
    created_at: datetime


@dataclass(frozen=True)
class ConsultationSummary:
    node_id: int
    node_name: str
    mention_count: int
    student_count: int
    last_seen_at: datetime


def extract_candidates_from_turn(
    client: Any,
    *,
    user_content: str,
    assistant_content: str,
    previous_context: str | None = None,
) -> list[dict]:
    prompt = f"""你是一个 Java 编程作业辅导系统的知识点抽取器。
请只根据本轮学生提问和助教回答，抽取学生实际咨询到的 Java 知识点候选。

要求：
1. 只输出 JSON 数组，不要输出 Markdown。
2. 最多 5 个元素。
3. 每个元素包含 name、confidence、evidence。
4. name 应是简短、可匹配正式知识图谱节点的中文知识点名称。
5. confidence 为 0 到 1 的数字。
6. evidence 摘录能说明为何抽取该知识点的简短证据。

上一轮上下文：
{previous_context or "无"}

学生提问：
{user_content}

助教回答：
{assistant_content}
"""
    response = client.chat.completions.create(
        model=settings.llm_model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    content = response.choices[0].message.content
    return _parse_candidate_json(content)


def _parse_candidate_json(content: str) -> list[dict]:
    start = content.find("[")
    end = content.rfind("]")
    if start < 0 or end < start:
        return []

    try:
        payload = json.loads(content[start : end + 1])
    except json.JSONDecodeError:
        return []

    if not isinstance(payload, list):
        return []

    candidates: list[dict] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        try:
            confidence = float(item.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))
        evidence = str(item.get("evidence") or "").strip()[:500]
        candidates.append({"name": name, "confidence": confidence, "evidence": evidence})
        if len(candidates) >= 5:
            break
    return candidates


def record_turn_knowledge_events(
    db: Session,
    client: Any,
    user: User,
    session: ChatSession,
    user_message: ChatMessage,
    assistant_message: ChatMessage,
    previous_context: str | None = None,
) -> list[str]:
    candidates = extract_candidates_from_turn(
        client,
        user_content=user_message.content,
        assistant_content=assistant_message.content,
        previous_context=previous_context,
    )
    candidate_by_name: dict[str, dict] = {}
    for candidate in candidates:
        candidate_by_name.setdefault(candidate["name"], candidate)
    if not candidate_by_name:
        return []

    nodes = (
        db.query(KnowledgeNode)
        .filter(KnowledgeNode.node_name.in_(list(candidate_by_name)))
        .all()
    )
    if not nodes:
        return []

    existing_node_ids = {
        row[0]
        for row in (
            db.query(ChatKnowledgeEvent.knowledge_node_id)
            .filter(
                ChatKnowledgeEvent.user_id == user.id,
                ChatKnowledgeEvent.session_id == session.id,
                ChatKnowledgeEvent.user_message_id == user_message.id,
                ChatKnowledgeEvent.assistant_message_id == assistant_message.id,
                ChatKnowledgeEvent.knowledge_node_id.in_([node.id for node in nodes]),
            )
            .all()
        )
    }

    events: list[ChatKnowledgeEvent] = []
    inserted_names: list[str] = []
    for node in sorted(nodes, key=lambda row: list(candidate_by_name).index(row.node_name)):
        if node.id in existing_node_ids:
            continue
        candidate = candidate_by_name[node.node_name]
        events.append(
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
        inserted_names.append(node.node_name)

    if not inserted_names:
        return []

    try:
        with db.begin_nested():
            db.add_all(events)
    except IntegrityError:
        return []
    return inserted_names


def list_recent_consultations(
    db: Session,
    user: User,
    limit: int = 20,
) -> list[ConsultationEventSummary]:
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
            event_id=event.id,
            session_id=session.id,
            session_title=session.title,
            user_message_id=event.user_message_id,
            assistant_message_id=event.assistant_message_id,
            node_id=node.id,
            node_name=node.node_name,
            confidence=event.confidence,
            evidence_text=event.evidence_text,
            created_at=event.created_at,
        )
        for event, node, session in rows
    ]


def list_student_consultations(
    db: Session,
    student_id: int,
    limit: int = 20,
) -> list[ConsultationSummary]:
    last_seen = func.max(ChatKnowledgeEvent.created_at).label("last_seen_at")
    rows = (
        db.query(
            KnowledgeNode.id,
            KnowledgeNode.node_name,
            func.count(ChatKnowledgeEvent.id).label("mention_count"),
            func.count(func.distinct(ChatKnowledgeEvent.user_id)).label("student_count"),
            last_seen,
            func.max(ChatKnowledgeEvent.id).label("last_event_id"),
        )
        .join(ChatKnowledgeEvent, ChatKnowledgeEvent.knowledge_node_id == KnowledgeNode.id)
        .filter(ChatKnowledgeEvent.user_id == student_id)
        .group_by(KnowledgeNode.id, KnowledgeNode.node_name)
        .order_by(
            func.count(ChatKnowledgeEvent.id).desc(),
            func.max(ChatKnowledgeEvent.created_at).desc(),
            func.max(ChatKnowledgeEvent.id).desc(),
        )
        .limit(limit)
        .all()
    )
    return [
        ConsultationSummary(
            node_id=row.id,
            node_name=row.node_name,
            mention_count=row.mention_count,
            student_count=row.student_count,
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
            KnowledgeNode.id,
            KnowledgeNode.node_name,
            func.count(ChatKnowledgeEvent.id).label("mention_count"),
            func.count(func.distinct(ChatKnowledgeEvent.user_id)).label("student_count"),
            func.max(ChatKnowledgeEvent.created_at).label("last_seen_at"),
            func.max(ChatKnowledgeEvent.id).label("last_event_id"),
        )
        .join(ChatKnowledgeEvent, ChatKnowledgeEvent.knowledge_node_id == KnowledgeNode.id)
        .join(User, User.id == ChatKnowledgeEvent.user_id)
    )
    if class_name:
        query = query.filter(User.class_name == class_name)

    rows = (
        query.group_by(KnowledgeNode.id, KnowledgeNode.node_name)
        .order_by(
            func.count(func.distinct(ChatKnowledgeEvent.user_id)).desc(),
            func.count(ChatKnowledgeEvent.id).desc(),
            func.max(ChatKnowledgeEvent.created_at).desc(),
            func.max(ChatKnowledgeEvent.id).desc(),
        )
        .limit(limit)
        .all()
    )
    return [
        ConsultationSummary(
            node_id=row.id,
            node_name=row.node_name,
            mention_count=row.mention_count,
            student_count=row.student_count,
            last_seen_at=row.last_seen_at,
        )
        for row in rows
    ]
