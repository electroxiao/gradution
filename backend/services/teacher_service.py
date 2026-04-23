import re

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.knowledge import KnowledgeNode, UserWeakPoint
from backend.models.knowledge_state import UserConceptMastery
from backend.models.user import User
from backend.schemas.teacher import (
    DashboardMetricResponse,
    GraphEdgeCreateRequest,
    GraphEdgeUpdateRequest,
    GraphNodeCreateRequest,
    GraphNodeUpdateRequest,
    PendingBatchApproveRequest,
    PendingBatchRejectRequest,
    GraphQueryResponse,
    TeacherKnowledgeNodeRefResponse,
    TeacherStudentMasteryResponse,
    TeacherStudentResponse,
    TeacherStudentWeakPointResponse,
)
from backend.services.chat_service import get_neo4j_driver
from backend.services.pending_batch_service import (
    approve_pending_batch,
    get_pending_batch_detail,
    list_pending_batches,
    reject_pending_batch,
)


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


def _split_search_terms(keyword: str) -> list[str]:
    normalized = keyword.strip()
    if not normalized:
        return []
    terms = [term.strip().lower() for term in re.split(r"[\s,，;；、]+", normalized) if term.strip()]
    if normalized.lower() not in terms:
        terms.insert(0, normalized.lower())
    return terms


def _compute_relevance_score(name: str, desc: str, terms: list[str], match_type: str = "match") -> int:
    if not terms:
        return 0
    name_lower = (name or "").lower()
    desc_lower = (desc or "").lower()
    phrase = terms[0]
    score = 0

    if name_lower == phrase:
        score += 1200
    elif name_lower.startswith(phrase):
        score += 900
    elif phrase in name_lower:
        score += 700

    if phrase and phrase in desc_lower:
        score += 120

    for term in terms:
        if not term:
            continue
        if name_lower == term:
            score += 280
        elif name_lower.startswith(term):
            score += 180
        elif term in name_lower:
            score += 110

        if term in desc_lower:
            score += 30

    if match_type == "neighbor":
        score -= 220
    return score


def _ensure_knowledge_nodes(
    db: Session,
    node_items: list[dict],
) -> list[TeacherKnowledgeNodeRefResponse]:
    if not node_items:
        return []

    existing = {
        row.node_name: row
        for row in db.query(KnowledgeNode).filter(KnowledgeNode.node_name.in_([item["node_name"] for item in node_items])).all()
    }
    responses = []
    for item in node_items:
        node_name = item["node_name"]
        row = existing.get(node_name)
        if not row:
            row = KnowledgeNode(node_name=node_name, node_type=item.get("node_type") or None)
            db.add(row)
            db.flush()
            existing[node_name] = row
        elif item.get("node_type") and row.node_type != item["node_type"]:
            row.node_type = item["node_type"]
        responses.append(
            TeacherKnowledgeNodeRefResponse(
                id=row.id,
                node_name=row.node_name,
                node_type=row.node_type,
                match_type=item.get("match_type") or "match",
                relevance_score=int(item.get("relevance_score") or 0),
            )
        )
    db.commit()
    return responses


def list_knowledge_node_refs(
    db: Session,
    keyword: str = "",
    include_neighbors: bool = False,
    limit: int = 200,
) -> list[TeacherKnowledgeNodeRefResponse]:
    terms = _split_search_terms(keyword)
    if not terms:
        rows = db.query(KnowledgeNode).order_by(KnowledgeNode.node_name.asc()).limit(limit).all()
        return [
            TeacherKnowledgeNodeRefResponse(id=row.id, node_name=row.node_name, node_type=row.node_type)
            for row in rows
        ]

    driver = get_neo4j_driver()
    query = """
    MATCH (n:Knowledge)
    WHERE any(term IN $terms WHERE
        toLower(n.name) CONTAINS term
        OR toLower(coalesce(properties(n)["desc"], "")) CONTAINS term
    )
    RETURN n.name AS node_name,
           coalesce(properties(n)["desc"], "") AS node_desc,
           coalesce(properties(n)["node_type"], "") AS node_type
    ORDER BY n.name ASC
    LIMIT $limit
    """
    items = []
    seen: set[tuple[str, str]] = set()
    with driver.session(database=settings.neo4j_db_name) as session:
        records = list(
            session.run(
                query,
                terms=terms,
                include_neighbors=include_neighbors,
                limit=limit,
            )
        )
        for record in records:
            node_name = record["node_name"]
            if not node_name or (node_name, "match") in seen:
                continue
            seen.add((node_name, "match"))
            items.append(
                {
                    "node_name": node_name,
                    "node_type": record["node_type"],
                    "match_type": "match",
                    "relevance_score": _compute_relevance_score(
                        node_name,
                        record["node_desc"],
                        terms,
                        "match",
                    ),
                }
            )

        if include_neighbors:
            neighbor_query = """
            UNWIND $names AS node_name
            MATCH (:Knowledge {name: node_name})-[r]-(neighbor:Knowledge)
            RETURN DISTINCT neighbor.name AS node_name,
                            coalesce(properties(neighbor)["desc"], "") AS node_desc,
                            coalesce(properties(neighbor)["node_type"], "") AS node_type
            LIMIT $limit
            """
            match_names = [item["node_name"] for item in items if item["match_type"] == "match"]
            for record in session.run(neighbor_query, names=match_names, limit=limit):
                node_name = record["node_name"]
                if not node_name or (node_name, "neighbor") in seen or any(item["node_name"] == node_name for item in items):
                    continue
                seen.add((node_name, "neighbor"))
                items.append(
                    {
                        "node_name": node_name,
                        "node_type": record["node_type"],
                        "match_type": "neighbor",
                        "relevance_score": _compute_relevance_score(
                            node_name,
                            record["node_desc"],
                            terms,
                            "neighbor",
                        ),
                    }
                )

    items.sort(key=lambda item: (-int(item["relevance_score"]), item["match_type"] != "match", item["node_name"]))
    return _ensure_knowledge_nodes(db, items[:limit])


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


def list_student_mastery(db: Session, student_id: int) -> list[TeacherStudentMasteryResponse]:
    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    rows = (
        db.query(UserConceptMastery, KnowledgeNode)
        .join(KnowledgeNode, UserConceptMastery.knowledge_node_id == KnowledgeNode.id)
        .filter(UserConceptMastery.student_id == student_id)
        .order_by(
            UserConceptMastery.mastery_score.asc(),
            UserConceptMastery.last_evaluated_at.desc(),
            KnowledgeNode.node_name.asc(),
        )
        .all()
    )
    return [
        TeacherStudentMasteryResponse(
            knowledge_node_id=node.id,
            node_name=node.node_name,
            mastery_score=int(mastery.mastery_score or 0),
            status=mastery.status,
            positive_evidence_count=int(mastery.positive_evidence_count or 0),
            negative_evidence_count=int(mastery.negative_evidence_count or 0),
            last_evaluated_at=mastery.last_evaluated_at,
        )
        for mastery, node in rows
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
    raw_nodes = []
    node_rows = []
    edge_rows = []
    node_id_map: dict[str, str] = {}
    terms = _split_search_terms(keyword)
    query = """
    MATCH (n:Knowledge)
    WHERE size($terms) = 0
       OR any(term IN $terms WHERE
           toLower(n.name) CONTAINS term
           OR toLower(coalesce(properties(n)["desc"], "")) CONTAINS term
       )
    RETURN n.name AS name,
           coalesce(properties(n)["desc"], "") AS desc,
           coalesce(properties(n)["node_type"], "") AS node_type
    ORDER BY n.name ASC
    LIMIT $limit
    """
    with driver.session(database=settings.neo4j_db_name) as session:
        for record in session.run(query, terms=terms, limit=limit):
            node_name = record["name"]
            raw_nodes.append(
                {
                    "label": node_name,
                    "name": node_name,
                    "desc": record["desc"],
                    "node_type": record["node_type"],
                    "search_match": bool(terms),
                    "relevance_score": _compute_relevance_score(
                        node_name,
                        record["desc"],
                        terms,
                        "match",
                    ),
                }
            )

        raw_nodes.sort(
            key=lambda item: (
                -int(item["relevance_score"]),
                item["name"],
            )
        )
        for index, item in enumerate(raw_nodes[:limit], start=1):
            node_id = str(index)
            item["id"] = node_id
            node_id_map[item["name"]] = node_id
            node_rows.append(item)

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


def list_pending_graph_batches(db: Session):
    return list_pending_batches(db)


def get_pending_graph_batch_detail(
    db: Session,
    batch_id: str,
):
    return get_pending_batch_detail(db, batch_id)


def approve_pending_graph_batch(
    db: Session,
    current_user: User,
    batch_id: str,
    payload: PendingBatchApproveRequest,
):
    return approve_pending_batch(db, current_user, batch_id, payload)


def reject_pending_graph_batch(
    db: Session,
    current_user: User,
    batch_id: str,
    payload: PendingBatchRejectRequest,
):
    return reject_pending_batch(db, current_user, batch_id, payload)


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
