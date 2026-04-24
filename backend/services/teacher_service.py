import re

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.assignment import Assignment, AssignmentQuestion, AssignmentQuestionKnowledgeNode, AssignmentSubmission
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
    TeacherStudentMasteryEvidenceResponse,
    TeacherStudentMasteryResponse,
    TeacherStudentResponse,
    TeacherStudentWeakPointResponse,
)
from backend.services.chat_service import get_neo4j_driver
from backend.services.chat_service import get_openai_client
from backend.services.pending_batch_service import (
    approve_pending_batch,
    get_pending_batch_detail,
    list_pending_batches,
    reject_pending_batch,
)


RELATION_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SEARCH_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_+#.-]+|[\u4e00-\u9fff]+")


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


def _extract_search_tokens(text: str) -> list[str]:
    return [token.lower() for token in SEARCH_TOKEN_PATTERN.findall(text or "")]


def _extract_aliases(name: str) -> list[str]:
    raw_parts = re.split(r"[()（）/\\|,，;；、]", name or "")
    aliases = []
    seen = set()
    for part in raw_parts:
        normalized = part.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            aliases.append(normalized)
    return aliases


def _compute_relevance_score(name: str, desc: str, terms: list[str], match_type: str = "match") -> int:
    if not terms:
        return 0
    name_lower = (name or "").lower()
    desc_lower = (desc or "").lower()
    phrase = terms[0]
    aliases = _extract_aliases(name)
    name_tokens = _extract_search_tokens(name)
    desc_tokens = _extract_search_tokens(desc)
    score = 0

    if phrase in aliases:
        score += 1800
    elif name_lower == phrase:
        score += 1200
    elif name_lower.startswith(phrase):
        score += 900
    elif phrase in name_lower:
        score += 700

    if phrase in name_tokens:
        score += 900
    elif any(token.startswith(phrase) for token in name_tokens):
        score += 260

    if phrase and phrase in desc_lower:
        score += 120
    if phrase in desc_tokens:
        score += 80

    for term in terms:
        if not term:
            continue
        if term in aliases:
            score += 520
        elif name_lower == term:
            score += 280
        elif name_lower.startswith(term):
            score += 180
        elif term in name_lower:
            score += 110

        if term in name_tokens:
            score += 220
        elif any(token.startswith(term) for token in name_tokens):
            score += 60

        if term in desc_lower:
            score += 30
        if term in desc_tokens:
            score += 20

    score -= max(len(name_tokens) - 2, 0) * 18
    score -= max(len(name or "") - max(len(phrase), 1), 0) // 12

    if match_type == "neighbor":
        score -= 220
    return score


def _resolve_candidate_limit(limit: int, include_neighbors: bool = False) -> int:
    multiplier = 20 if include_neighbors else 12
    baseline = 240 if include_neighbors else 120
    return max(limit, min(2000, max(baseline, limit * multiplier)))


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
    candidate_limit = _resolve_candidate_limit(limit, include_neighbors=include_neighbors)
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
    LIMIT $candidate_limit
    """
    items = []
    seen: set[tuple[str, str]] = set()
    with driver.session(database=settings.neo4j_db_name) as session:
        records = list(
            session.run(
                query,
                terms=terms,
                candidate_limit=candidate_limit,
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
            LIMIT $candidate_limit
            """
            match_names = [item["node_name"] for item in items if item["match_type"] == "match"]
            for record in session.run(neighbor_query, names=match_names, candidate_limit=candidate_limit):
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
            evidence=_list_student_mastery_evidence(db, student_id, node.id),
        )
        for mastery, node in rows
    ]


def _list_student_mastery_evidence(
    db: Session,
    student_id: int,
    knowledge_node_id: int,
    limit: int = 8,
) -> list[TeacherStudentMasteryEvidenceResponse]:
    rows = (
        db.query(AssignmentSubmission, Assignment, AssignmentQuestion)
        .join(Assignment, AssignmentSubmission.assignment_id == Assignment.id)
        .join(AssignmentQuestion, AssignmentSubmission.question_id == AssignmentQuestion.id)
        .join(
            AssignmentQuestionKnowledgeNode,
            AssignmentQuestionKnowledgeNode.question_id == AssignmentQuestion.id,
        )
        .filter(
            AssignmentSubmission.student_id == student_id,
            AssignmentQuestionKnowledgeNode.knowledge_node_id == knowledge_node_id,
        )
        .order_by(AssignmentSubmission.submitted_at.desc(), AssignmentSubmission.id.desc())
        .limit(limit)
        .all()
    )
    return [
        _mastery_evidence_response(submission, assignment, question)
        for submission, assignment, question in rows
    ]


def _mastery_evidence_response(
    submission: AssignmentSubmission,
    assignment: Assignment,
    question: AssignmentQuestion,
) -> TeacherStudentMasteryEvidenceResponse:
    ai_review = submission.ai_review_json if isinstance(submission.ai_review_json, dict) else {}
    included = not bool(submission.excluded_from_mastery_update)
    if not included:
        contribution = "excluded"
    elif submission.status == "accepted":
        contribution = "positive"
    else:
        contribution = "negative"

    return TeacherStudentMasteryEvidenceResponse(
        submission_id=submission.id,
        assignment_id=assignment.id,
        assignment_title=assignment.title,
        question_id=question.id,
        question_title=question.title or "未命名题目",
        status=submission.status,
        decision_source=submission.final_decision_source,
        trust_label=submission.trust_label,
        included_in_mastery=included,
        contribution=contribution,
        duration_seconds=submission.duration_seconds,
        submitted_at=submission.submitted_at,
        ai_score=ai_review.get("score") if ai_review else None,
        ai_confidence=ai_review.get("confidence") if ai_review else None,
        ai_summary=ai_review.get("summary") if ai_review else None,
    )


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
    candidate_limit = _resolve_candidate_limit(limit)
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
    LIMIT $candidate_limit
    """
    with driver.session(database=settings.neo4j_db_name) as session:
        for record in session.run(query, terms=terms, candidate_limit=candidate_limit):
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
    name = payload.name.strip()
    desc = payload.desc.strip()
    node_type = (payload.node_type or "").strip()
    with driver.session(database=settings.neo4j_db_name) as session:
        existing = session.run(
            "MATCH (n:Knowledge {name: $name}) RETURN n.name AS name LIMIT 1",
            name=name,
        ).single()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Node already exists")

        session.run(
            """
            CREATE (n:Knowledge {name: $name, desc: $desc, node_type: $node_type})
            """,
            name=name,
            desc=desc,
            node_type=node_type,
        )
    return {"ok": True}


def create_graph_node_with_db_sync(db: Session | None, payload: GraphNodeCreateRequest) -> dict:
    result = create_graph_node(payload)
    if db is not None:
        _ensure_knowledge_nodes(
            db,
            [{"node_name": payload.name.strip(), "node_type": (payload.node_type or "").strip(), "relevance_score": 0}],
        )
    return result


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
    source_name = payload.source.strip()
    target_name = payload.target.strip()
    created_nodes: list[dict] = []
    with driver.session(database=settings.neo4j_db_name) as session:
        created_nodes.extend(_ensure_node_exists_or_create(session, source_name))
        created_nodes.extend(_ensure_node_exists_or_create(session, target_name))
        session.run(
            f"""
            MATCH (src:Knowledge {{name: $source}})
            MATCH (tgt:Knowledge {{name: $target}})
            MERGE (src)-[r:{relation}]->(tgt)
            """,
            source=source_name,
            target=target_name,
        )
    return {"ok": True, "created_nodes": created_nodes}


def create_graph_edge_with_db_sync(db: Session | None, payload: GraphEdgeCreateRequest) -> dict:
    result = create_graph_edge(payload)
    if db is not None and result.get("created_nodes"):
        _ensure_knowledge_nodes(
            db,
            [
                {
                    "node_name": item["name"],
                    "node_type": "",
                    "relevance_score": 0,
                }
                for item in result["created_nodes"]
            ],
        )
    return result


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


def _ensure_node_exists_or_create(session, node_name: str) -> list[dict]:
    normalized = node_name.strip()
    row = session.run(
        "MATCH (n:Knowledge {name: $name}) RETURN n.name AS name LIMIT 1",
        name=normalized,
    ).single()
    if row:
        return []
    generated_desc = _generate_graph_node_description_text(normalized)
    session.run(
        """
        CREATE (n:Knowledge {name: $name, desc: $desc, node_type: ""})
        """,
        name=normalized,
        desc=generated_desc,
    )
    return [{"name": normalized, "desc_generated": bool(generated_desc)}]


def _generate_graph_node_description_text(node_name: str) -> str:
    try:
        return str(generate_graph_node_description(node_name).get("desc") or "").strip()
    except HTTPException:
        return ""


def generate_graph_node_description(node_name: str) -> dict:
    normalized = node_name.strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Node name is required")

    prompt = f"""
你是一名 Java 教学知识图谱编辑助手。请根据知识点名称生成一段简洁、准确、适合教学管理页展示的描述。

知识点名称：{normalized}

要求：
1. 用中文输出。
2. 1 到 2 句话，控制在 40 到 90 字。
3. 优先解释“这是什么”和“它通常用来解决什么问题”。
4. 不要使用列表，不要输出标题，不要加引号。
"""
    client = get_openai_client()
    try:
        response = client.chat.completions.create(
            model=settings.llm_model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        content = (response.choices[0].message.content or "").strip()
        if not content:
            raise ValueError("empty response")
        return {"desc": content}
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"生成节点描述失败：{error}") from error


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
