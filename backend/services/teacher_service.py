import re

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.knowledge import KnowledgeNode, UserWeakPoint
from backend.models.user import User
from backend.schemas.teacher import (
    DashboardMetricResponse,
    GraphEdgeCreateRequest,
    GraphEdgeUpdateRequest,
    GraphNodeCreateRequest,
    GraphNodeUpdateRequest,
    GraphQueryResponse,
    TeacherStudentResponse,
    TeacherStudentWeakPointResponse,
)
from backend.services.chat_service import get_neo4j_driver


RELATION_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def list_students_with_weak_points(db: Session) -> list[TeacherStudentResponse]:
    rows = (
        db.query(
            User.id,
            User.username,
            func.count(UserWeakPoint.id).label("weak_point_count"),
        )
        .outerjoin(
            UserWeakPoint,
            (UserWeakPoint.user_id == User.id) & (UserWeakPoint.status == "unmastered"),
        )
        .filter(User.role == "student")
        .group_by(User.id, User.username)
        .order_by(User.username.asc())
        .all()
    )
    return [
        TeacherStudentResponse(
            id=row.id,
            username=row.username,
            weak_point_count=int(row.weak_point_count or 0),
        )
        for row in rows
    ]


def list_student_weak_points(db: Session, student_id: int) -> list[TeacherStudentWeakPointResponse]:
    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    rows = (
        db.query(UserWeakPoint, KnowledgeNode)
        .join(KnowledgeNode, UserWeakPoint.knowledge_node_id == KnowledgeNode.id)
        .filter(UserWeakPoint.user_id == student_id, UserWeakPoint.status == "unmastered")
        .order_by(UserWeakPoint.last_seen_at.desc())
        .all()
    )
    return [
        TeacherStudentWeakPointResponse(
            id=node.id,
            node_name=node.node_name,
            status=weak_point.status,
            first_seen_at=weak_point.first_seen_at,
            last_seen_at=weak_point.last_seen_at,
        )
        for weak_point, node in rows
    ]


def get_weak_point_dashboard(db: Session, limit: int = 10) -> DashboardMetricResponse:
    total_students = db.query(func.count(User.id)).filter(User.role == "student").scalar() or 0
    total_unmastered = (
        db.query(func.count(UserWeakPoint.id))
        .filter(UserWeakPoint.status == "unmastered")
        .scalar()
        or 0
    )
    affected_students = (
        db.query(func.count(func.distinct(UserWeakPoint.user_id)))
        .filter(UserWeakPoint.status == "unmastered")
        .scalar()
        or 0
    )
    top_rows = (
        db.query(
            KnowledgeNode.id,
            KnowledgeNode.node_name,
            func.count(UserWeakPoint.id).label("mark_count"),
        )
        .join(UserWeakPoint, UserWeakPoint.knowledge_node_id == KnowledgeNode.id)
        .filter(UserWeakPoint.status == "unmastered")
        .group_by(KnowledgeNode.id, KnowledgeNode.node_name)
        .order_by(func.count(UserWeakPoint.id).desc(), KnowledgeNode.node_name.asc())
        .limit(limit)
        .all()
    )
    return DashboardMetricResponse(
        total_students=int(total_students),
        total_unmastered_weak_points=int(total_unmastered),
        affected_students=int(affected_students),
        top_nodes=[
            {
                "id": row.id,
                "node_name": row.node_name,
                "mark_count": int(row.mark_count or 0),
            }
            for row in top_rows
        ],
    )


def get_graph(keyword: str = "", limit: int = 1000) -> GraphQueryResponse:
    driver = get_neo4j_driver()
    node_rows = []
    edge_rows = []
    node_id_map: dict[str, str] = {}
    query = """
    MATCH (n:Knowledge)
    WHERE $keyword = "" 
       OR toLower(n.name) CONTAINS toLower($keyword)
       OR toLower(coalesce(properties(n)["desc"], "")) CONTAINS toLower($keyword)
    RETURN n.name AS name,
           coalesce(properties(n)["desc"], "") AS desc,
           coalesce(properties(n)["node_type"], "") AS node_type
    ORDER BY n.name ASC
    LIMIT $limit
    """
    with driver.session(database=settings.neo4j_db_name) as session:
        for index, record in enumerate(session.run(query, keyword=keyword.strip(), limit=limit), start=1):
            node_id = str(index)
            node_name = record["name"]
            node_id_map[node_name] = node_id
            node_rows.append(
                {
                    "id": node_id,
                    "label": node_name,
                    "name": node_name,
                    "desc": record["desc"],
                    "node_type": record["node_type"],
                }
            )

        if node_rows:
            edge_query = """
            UNWIND $names AS node_name
            MATCH (src:Knowledge {name: node_name})-[r]->(tgt:Knowledge)
            WHERE tgt.name IN $names
            RETURN src.name AS source,
                   type(r) AS relation,
                   tgt.name AS target
            """
            names = [row["name"] for row in node_rows]
            seen = set()
            edge_index = len(node_rows) + 1
            for record in session.run(edge_query, names=names):
                source_name = record["source"]
                target_name = record["target"]
                source_id = node_id_map.get(source_name)
                target_id = node_id_map.get(target_name)
                if not source_id or not target_id:
                    continue
                edge_key = _build_edge_id(source_name, record["relation"], target_name)
                if edge_key in seen:
                    continue
                seen.add(edge_key)
                edge_rows.append(
                    {
                        "id": str(edge_index),
                        "edge_key": edge_key,
                        "source": source_id,
                        "target": target_id,
                        "source_name": source_name,
                        "target_name": target_name,
                        "label": record["relation"],
                        "relation": record["relation"],
                    }
                )
                edge_index += 1

    return GraphQueryResponse(nodes=node_rows, edges=edge_rows)


def create_graph_node(payload: GraphNodeCreateRequest) -> dict:
    driver = get_neo4j_driver()
    with driver.session(database=settings.neo4j_db_name) as session:
        existing = session.run(
            "MATCH (n:Knowledge {name: $name}) RETURN n.name AS name LIMIT 1",
            name=payload.name.strip(),
        ).single()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Node already exists")

        session.run(
            """
            CREATE (n:Knowledge {name: $name, desc: $desc, node_type: $node_type})
            """,
            name=payload.name.strip(),
            desc=payload.desc.strip(),
            node_type=(payload.node_type or "").strip(),
        )
    return {"ok": True}


def update_graph_node(node_name: str, payload: GraphNodeUpdateRequest) -> dict:
    driver = get_neo4j_driver()
    with driver.session(database=settings.neo4j_db_name) as session:
        node = session.run(
            "MATCH (n:Knowledge {name: $name}) RETURN n.name AS name LIMIT 1",
            name=node_name,
        ).single()
        if not node:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")

        if payload.name.strip() != node_name:
            duplicate = session.run(
                "MATCH (n:Knowledge {name: $name}) RETURN n.name AS name LIMIT 1",
                name=payload.name.strip(),
            ).single()
            if duplicate:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target node name already exists")

        session.run(
            """
            MATCH (n:Knowledge {name: $current_name})
            SET n.name = $next_name,
                n.desc = $desc,
                n.node_type = $node_type
            """,
            current_name=node_name,
            next_name=payload.name.strip(),
            desc=payload.desc.strip(),
            node_type=(payload.node_type or "").strip(),
        )
    return {"ok": True}


def delete_graph_node(node_name: str) -> dict:
    driver = get_neo4j_driver()
    with driver.session(database=settings.neo4j_db_name) as session:
        node = session.run(
            "MATCH (n:Knowledge {name: $name}) RETURN n.name AS name LIMIT 1",
            name=node_name,
        ).single()
        if not node:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
        session.run("MATCH (n:Knowledge {name: $name}) DETACH DELETE n", name=node_name)
    return {"ok": True}


def create_graph_edge(payload: GraphEdgeCreateRequest) -> dict:
    relation = _normalize_relation(payload.relation)
    driver = get_neo4j_driver()
    with driver.session(database=settings.neo4j_db_name) as session:
        _ensure_node_exists(session, payload.source.strip())
        _ensure_node_exists(session, payload.target.strip())
        session.run(
            f"""
            MATCH (src:Knowledge {{name: $source}})
            MATCH (tgt:Knowledge {{name: $target}})
            MERGE (src)-[r:{relation}]->(tgt)
            """,
            source=payload.source.strip(),
            target=payload.target.strip(),
        )
    return {"ok": True}


def update_graph_edge(edge_id: str, payload: GraphEdgeUpdateRequest) -> dict:
    source, relation, target = _parse_edge_id(edge_id)
    delete_graph_edge(edge_id)
    create_graph_edge(
        GraphEdgeCreateRequest(
            source=payload.source.strip(),
            target=payload.target.strip(),
            relation=payload.relation.strip(),
        )
    )
    return {
        "ok": True,
        "previous": {"source": source, "relation": relation, "target": target},
    }


def delete_graph_edge(edge_id: str) -> dict:
    source, relation, target = _parse_edge_id(edge_id)
    driver = get_neo4j_driver()
    with driver.session(database=settings.neo4j_db_name) as session:
        result = session.run(
            f"""
            MATCH (src:Knowledge {{name: $source}})-[r:{relation}]->(tgt:Knowledge {{name: $target}})
            WITH r LIMIT 1
            DELETE r
            RETURN 1 AS deleted_count
            """,
            source=source,
            target=target,
        ).single()
        deleted_count = int(result["deleted_count"] or 0) if result else 0
        if deleted_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edge not found")
    return {"ok": True}


def _ensure_node_exists(session, node_name: str) -> None:
    row = session.run(
        "MATCH (n:Knowledge {name: $name}) RETURN n.name AS name LIMIT 1",
        name=node_name,
    ).single()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node not found: {node_name}")


def _normalize_relation(relation: str) -> str:
    normalized = relation.strip().upper().replace(" ", "_")
    if not RELATION_PATTERN.match(normalized):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid relation name")
    return normalized


def _build_edge_id(source: str, relation: str, target: str) -> str:
    return f"{source}|||{relation}|||{target}"


def _parse_edge_id(edge_id: str) -> tuple[str, str, str]:
    parts = edge_id.split("|||")
    if len(parts) != 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid edge id")
    source, relation, target = parts
    return source, _normalize_relation(relation), target
