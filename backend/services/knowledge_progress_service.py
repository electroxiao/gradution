from sqlalchemy.orm import Session

from backend.models.knowledge import KnowledgeNode, UserWeakPoint
from backend.models.knowledge_state import UserKnowledgeState
from backend.models.user import User

GRAPH_STATUS_COLOR_MAP = {
    "weak": "#ef4444",
    "mastered": "#22c55e",
    "learning": "#f59e0b",
    "unknown": "#94a3b8",
}


def get_graph_node_color(status: str) -> str:
    return GRAPH_STATUS_COLOR_MAP.get(status or "unknown", GRAPH_STATUS_COLOR_MAP["unknown"])


def resolve_knowledge_node_by_name(db: Session, node_name: str) -> KnowledgeNode | None:
    return db.query(KnowledgeNode).filter(KnowledgeNode.node_name == node_name).first()


def get_or_create_knowledge_node(db: Session, node_name: str) -> KnowledgeNode:
    node = resolve_knowledge_node_by_name(db, node_name)
    if node:
        return node

    node = KnowledgeNode(node_name=node_name)
    db.add(node)
    db.flush()
    return node


def get_knowledge_state(db: Session, user: User, node_name: str) -> UserKnowledgeState | None:
    return (
        db.query(UserKnowledgeState)
        .filter(
            UserKnowledgeState.user_id == user.id,
            UserKnowledgeState.node_id == node_name,
        )
        .first()
    )


def set_knowledge_state_status(db: Session, user: User, node_name: str, status: str) -> UserKnowledgeState:
    knowledge_state = get_knowledge_state(db, user, node_name)
    if not knowledge_state:
        knowledge_state = UserKnowledgeState(
            user_id=user.id,
            node_id=node_name,
            status=status,
        )
        db.add(knowledge_state)
        return knowledge_state

    knowledge_state.status = status
    return knowledge_state


def get_weak_point_for_node(
    db: Session,
    user: User,
    knowledge_node_id: int,
) -> UserWeakPoint | None:
    return (
        db.query(UserWeakPoint)
        .filter(
            UserWeakPoint.user_id == user.id,
            UserWeakPoint.knowledge_node_id == knowledge_node_id,
        )
        .first()
    )


def get_weak_point_for_node_name(db: Session, user: User, node_name: str) -> UserWeakPoint | None:
    node = resolve_knowledge_node_by_name(db, node_name)
    if not node:
        return None
    return get_weak_point_for_node(db, user, node.id)


def list_unmastered_weak_point_rows(db: Session, user: User) -> list[tuple[UserWeakPoint, KnowledgeNode]]:
    return (
        db.query(UserWeakPoint, KnowledgeNode)
        .join(KnowledgeNode, UserWeakPoint.knowledge_node_id == KnowledgeNode.id)
        .filter(UserWeakPoint.user_id == user.id, UserWeakPoint.status == "unmastered")
        .order_by(UserWeakPoint.last_seen_at.desc())
        .all()
    )


def list_unmastered_weak_node_names(db: Session, user: User) -> list[str]:
    return [node.node_name for _, node in list_unmastered_weak_point_rows(db, user)]


def build_graph_state_map(db: Session, user: User) -> dict[str, str]:
    rows = db.query(UserKnowledgeState).filter(UserKnowledgeState.user_id == user.id).all()
    states = {row.node_id: row.status for row in rows}

    for node_name in list_unmastered_weak_node_names(db, user):
        if states.get(node_name) != "mastered":
            states[node_name] = "weak"

    return states


def mark_node_weak(
    db: Session,
    user: User,
    node_name: str,
    *,
    source_session_id: int | None = None,
) -> bool:
    node = get_or_create_knowledge_node(db, node_name)
    weak_point = get_weak_point_for_node(db, user, node.id)
    is_new_or_reactivated = False

    if not weak_point:
        weak_point = UserWeakPoint(
            user_id=user.id,
            knowledge_node_id=node.id,
            source_session_id=source_session_id,
            status="unmastered",
        )
        db.add(weak_point)
        is_new_or_reactivated = True
    else:
        if weak_point.status != "unmastered":
            weak_point.status = "unmastered"
            is_new_or_reactivated = True
        weak_point.source_session_id = source_session_id

    set_knowledge_state_status(db, user, node_name, "weak")
    return is_new_or_reactivated


def mark_node_mastered(db: Session, user: User, node_name: str) -> bool:
    set_knowledge_state_status(db, user, node_name, "mastered")

    weak_point = get_weak_point_for_node_name(db, user, node_name)
    if weak_point:
        weak_point.status = "mastered"

    return True


def mark_weak_point_mastered_by_node_id(db: Session, user: User, node_id: int) -> str | None:
    weak_point = get_weak_point_for_node(db, user, node_id)
    if not weak_point:
        return None

    weak_point.status = "mastered"
    node = db.query(KnowledgeNode).filter(KnowledgeNode.id == weak_point.knowledge_node_id).first()
    if not node:
        return None

    set_knowledge_state_status(db, user, node.node_name, "mastered")
    return node.node_name
