from __future__ import annotations

import json
import re
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
    formal_nodes: list[dict] | None = None,
) -> list[dict]:
    formal_node_options = "[]"
    if formal_nodes:
        formal_node_options = json.dumps(
            [{"id": int(node["id"]), "name": str(node["name"])} for node in formal_nodes],
            ensure_ascii=False,
            separators=(",", ":"),
        )

    prompt = f"""你是一个 Java 编程作业辅导系统的知识点抽取器。
请只根据本轮学生提问和助教回答，抽取学生实际咨询到的 Java 知识点候选。

要求：
1. 只输出 JSON 数组，不要输出 Markdown。
2. 最多 5 个元素。
3. 只能从下面的正式知识图谱节点中选择，不允许创造新知识点。
4. 每个元素只包含 node_id、node_name。
5. node_id 和 node_name 必须来自正式知识图谱节点列表。
6. 如果没有合适节点，返回空数组。
7. 为兼容旧格式，也可以额外包含 name，但 node_id 优先。

正式知识图谱节点：
{formal_node_options}

旧格式兼容要求：
如果无法输出 node_id，才输出 name。
name 应是简短、可匹配正式知识图谱节点的中文知识点名称。

上一轮上下文：
{previous_context or "无"}

学生提问：
{user_content}

助教回答：
{assistant_content}
"""
    try:
        response = client.chat.completions.create(
            model=settings.llm_model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        content = response.choices[0].message.content or "[]"
    except Exception:
        return []
    return _parse_candidate_json(content)


def _parse_candidate_json(content: str) -> list[dict]:
    if not isinstance(content, str):
        return []

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
        node_name = str(item.get("node_name") or "").strip()
        name = node_name or str(item.get("name") or "").strip()
        if not name:
            continue
        candidates.append({"name": name})
        node_id = item.get("node_id")
        try:
            if node_id is not None:
                candidates[-1]["node_id"] = int(node_id)
        except (TypeError, ValueError):
            pass
        if node_name:
            candidates[-1]["node_name"] = node_name
        if len(candidates) >= 5:
            break
    return candidates


_PARENTHETICAL_RE = re.compile(r"\s*(?:\([^()]*\)|（[^（）]*）)\s*")


def _strip_parenthetical(name: str) -> str:
    return _PARENTHETICAL_RE.sub("", name).strip()


def _formal_node_aliases(node_name: str) -> set[str]:
    aliases = {node_name}

    stripped = _strip_parenthetical(node_name)
    if stripped:
        aliases.add(stripped)

    expanded_aliases = set(aliases)
    for alias in aliases:
        if "方法" in alias:
            expanded_aliases.add(alias.replace("方法", "函数"))
        if "函数" in alias:
            expanded_aliases.add(alias.replace("函数", "方法"))
    return {alias for alias in expanded_aliases if alias}


def _resolve_candidate_nodes(db: Session, candidate_by_name: dict[str, dict]) -> list[tuple[KnowledgeNode, dict]]:
    candidate_names = list(candidate_by_name)
    exact_nodes = (
        db.query(KnowledgeNode)
        .filter(KnowledgeNode.node_name.in_(candidate_names))
        .all()
    )
    exact_by_name = {node.node_name: node for node in exact_nodes if node.node_name in candidate_by_name}

    all_nodes = db.query(KnowledgeNode).all()
    alias_to_node: dict[str, KnowledgeNode] = {}
    for node in all_nodes:
        for alias in _formal_node_aliases(node.node_name):
            alias_to_node.setdefault(alias, node)

    resolved: list[tuple[KnowledgeNode, dict]] = []
    seen_node_ids: set[int] = set()
    for candidate_name in candidate_names:
        node = exact_by_name.get(candidate_name) or alias_to_node.get(candidate_name)
        if node is None or node.id in seen_node_ids:
            continue
        seen_node_ids.add(node.id)
        resolved.append((node, candidate_by_name[candidate_name]))
    return resolved


def _formal_nodes_for_prompt(db: Session) -> list[dict]:
    return [
        {"id": node.id, "name": node.node_name}
        for node in db.query(KnowledgeNode).order_by(KnowledgeNode.id).all()
    ]


def _resolve_candidate_node_ids(db: Session, candidates: list[dict]) -> list[tuple[KnowledgeNode, dict]]:
    node_ids = []
    candidate_by_id: dict[int, dict] = {}
    for candidate in candidates:
        node_id = candidate.get("node_id")
        if not isinstance(node_id, int):
            continue
        if node_id in candidate_by_id:
            continue
        node_ids.append(node_id)
        candidate_by_id[node_id] = candidate

    if not node_ids:
        return []

    nodes = db.query(KnowledgeNode).filter(KnowledgeNode.id.in_(node_ids)).all()
    node_by_id = {node.id: node for node in nodes}

    resolved: list[tuple[KnowledgeNode, dict]] = []
    for node_id in node_ids:
        node = node_by_id.get(node_id)
        if node is None:
            continue
        candidate = candidate_by_id[node_id]
        candidate_node_name = str(candidate.get("node_name") or candidate.get("name") or "").strip()
        if candidate_node_name and candidate_node_name != node.node_name:
            continue
        resolved.append((node, candidate))
    return resolved


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
        formal_nodes=_formal_nodes_for_prompt(db),
    )
    resolved_nodes = _resolve_candidate_node_ids(db, candidates)
    if not resolved_nodes:
        resolved_nodes = _resolve_candidate_nodes(
            db,
            {candidate["name"]: candidate for candidate in candidates if candidate.get("name")},
        )
    if not resolved_nodes:
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
                ChatKnowledgeEvent.knowledge_node_id.in_([node.id for node, _candidate in resolved_nodes]),
            )
            .all()
        )
    }

    events: list[ChatKnowledgeEvent] = []
    inserted_names: list[str] = []
    for node, candidate in resolved_nodes:
        if node.id in existing_node_ids:
            continue
        events.append(
            ChatKnowledgeEvent(
                user_id=user.id,
                session_id=session.id,
                user_message_id=user_message.id,
                assistant_message_id=assistant_message.id,
                knowledge_node_id=node.id,
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
