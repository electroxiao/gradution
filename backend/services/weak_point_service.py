from sqlalchemy.orm import Session

from backend.models.chat import ChatSession
from backend.models.knowledge import KnowledgeNode, UserWeakPoint
from backend.models.user import User
from backend.schemas.weak_point import WeakPointResponse


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
        node = db.query(KnowledgeNode).filter(KnowledgeNode.node_name == node_name).first()
        if not node:
            node = KnowledgeNode(node_name=node_name)
            db.add(node)
            db.flush()

        weak_point = (
            db.query(UserWeakPoint)
            .filter(
                UserWeakPoint.user_id == user.id,
                UserWeakPoint.knowledge_node_id == node.id,
            )
            .first()
        )
        if not weak_point:
            weak_point = UserWeakPoint(
                user_id=user.id,
                knowledge_node_id=node.id,
                source_session_id=session.id,
                status="unmastered",
            )
            db.add(weak_point)
            added.append(node_name)
            continue

        if weak_point.status != "unmastered":
            weak_point.status = "unmastered"
            added.append(node_name)
        weak_point.source_session_id = session.id

    db.commit()
    return added


def list_unmastered_weak_points(db: Session, user: User) -> list[WeakPointResponse]:
    rows = (
        db.query(UserWeakPoint, KnowledgeNode)
        .join(KnowledgeNode, UserWeakPoint.knowledge_node_id == KnowledgeNode.id)
        .filter(UserWeakPoint.user_id == user.id, UserWeakPoint.status == "unmastered")
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
    weak_point = (
        db.query(UserWeakPoint)
        .filter(UserWeakPoint.user_id == user.id, UserWeakPoint.knowledge_node_id == node_id)
        .first()
    )
    if weak_point:
        weak_point.status = "mastered"
        db.commit()
