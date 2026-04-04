from sqlalchemy.orm import Session

from backend.models.chat import ChatSession
from backend.models.knowledge import KnowledgeNode, UserWeakPoint
from backend.models.user import User
from backend.schemas.weak_point import WeakPointResponse
from backend.services.knowledge_progress_service import (
    list_unmastered_weak_point_rows,
    mark_node_weak,
    mark_weak_point_mastered_by_node_id,
)


def extract_core_nodes(facts: list) -> list[str]:
    nodes: set[str] = set()
    for fact in facts or []:
        if not isinstance(fact, dict):
            continue
        if fact.get("type") == "weak_point" and fact.get("node_name"):
            nodes.add(fact["node_name"])

    if nodes:
        return sorted(nodes)

    for fact in facts or []:
        if not isinstance(fact, dict):
            continue
        if fact.get("type") == "selected_path" and fact.get("target"):
            nodes.add(fact["target"])
    return sorted(nodes)

def upsert_weak_points(db: Session, user: User, session: ChatSession, node_names: list[str]) -> list[str]:
    added: list[str] = []
    for node_name in node_names:
        if mark_node_weak(db, user, node_name, source_session_id=session.id):
            added.append(node_name)

    db.commit()
    return added


def list_unmastered_weak_points(db: Session, user: User) -> list[WeakPointResponse]:
    rows = list_unmastered_weak_point_rows(db, user)
    return [
        WeakPointResponse(
            id=node.id,
            node_name=node.node_name,
            status="weak",
            first_seen_at=weak_point.first_seen_at,
            last_seen_at=weak_point.last_seen_at,
        )
        for weak_point, node in rows
    ]


def list_history_weak_points(db: Session, user: User) -> list[WeakPointResponse]:
    rows = (
        db.query(UserWeakPoint, KnowledgeNode)
        .join(KnowledgeNode, UserWeakPoint.knowledge_node_id == KnowledgeNode.id)
        .filter(UserWeakPoint.user_id == user.id, UserWeakPoint.status != "unmastered")
        .order_by(UserWeakPoint.last_seen_at.desc())
        .all()
    )
    return [
        WeakPointResponse(
            id=node.id,
            node_name=node.node_name,
            status=weak_point.status,
            first_seen_at=weak_point.first_seen_at,
            last_seen_at=weak_point.last_seen_at,
        )
        for weak_point, node in rows
    ]


def mark_weak_point_mastered(db: Session, user: User, node_id: int) -> None:
    if mark_weak_point_mastered_by_node_id(db, user, node_id):
        db.commit()
