import json
from datetime import datetime

from fastapi import HTTPException, status
from neo4j import GraphDatabase
from openai import OpenAI
from sqlalchemy.orm import Session, joinedload

from backend.core.config import settings
from backend.models.knowledge import (
    PendingNodeProposal,
    PendingProposalBatch,
    PendingProposalBatchEdge,
    PendingProposalBatchNode,
    UserWeakPoint,
)
from backend.models.user import User
from backend.schemas.teacher import (
    PendingBatchApproveRequest,
    PendingBatchDetailBatchResponse,
    PendingBatchDetailResponse,
    PendingBatchGraphEdgeResponse,
    PendingBatchGraphNodeResponse,
    PendingBatchRejectRequest,
    PendingBatchSummaryResponse,
    PendingNodeApproveRequest,
    PendingNodeRejectRequest,
)
from backend.services.pending_proposal_service import (
    approve_pending_proposal,
    get_pending_proposal_context,
    list_pending_proposals_for_anchor,
    reject_pending_proposal,
    serialize_pending_proposal,
)


def _batch_public_id(batch_id: int) -> str:
    return f"batch:{batch_id}"


def _legacy_batch_public_id(proposal_id: int) -> str:
    return f"legacy:{proposal_id}"


def _batch_node_public_id(node_id: int) -> str:
    return f"pending-batch-node:{node_id}"


def _batch_edge_public_id(edge_id: int) -> str:
    return f"pending-batch-edge:{edge_id}"


def _context_node_public_id(name: str) -> str:
    return f"context:{name}"


def _normalize_relation(relation: str) -> str:
    normalized = (relation or "DEPENDS_ON").strip().upper().replace(" ", "_")
    if not normalized or not normalized.replace("_", "").isalnum() or not normalized[0].isalpha():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid relation name")
    return normalized


def _neo4j_node_exists(session, name: str) -> bool:
    row = session.run(
        "MATCH (n:Knowledge {name: $name}) RETURN n.name AS name LIMIT 1",
        name=name,
    ).single()
    return bool(row)


def _existing_graph_node_names(names: list[str]) -> set[str]:
    candidate_names = [name.strip() for name in names if isinstance(name, str) and name.strip()]
    if not candidate_names:
        return set()
    driver = GraphDatabase.driver(settings.neo4j_uri, auth=settings.neo4j_auth)
    try:
        with driver.session(database=settings.neo4j_db_name) as session:
            rows = session.run(
                """
                MATCH (n:Knowledge)
                WHERE n.name IN $names
                RETURN DISTINCT n.name AS name
                """,
                names=candidate_names,
            )
            return {row["name"] for row in rows if row.get("name")}
    finally:
        driver.close()


def _fetch_graph_nodes(names: set[str]) -> dict[str, str]:
    names = {name for name in names if name}
    if not names:
        return {}
    driver = GraphDatabase.driver(settings.neo4j_uri, auth=settings.neo4j_auth)
    try:
        with driver.session(database=settings.neo4j_db_name) as session:
            rows = session.run(
                """
                MATCH (n:Knowledge)
                WHERE n.name IN $names
                RETURN n.name AS name, coalesce(n.desc, '') AS desc
                """,
                names=list(names),
            )
            return {row["name"]: row["desc"] or "" for row in rows}
    finally:
        driver.close()


def _build_question_excerpt(question: str) -> str:
    compact = " ".join((question or "").split())
    return compact[:180] + ("..." if len(compact) > 180 else "")


def _ensure_node_desc(*, name: str, desc: str, reason: str, question_excerpt: str, anchor_name: str) -> str:
    normalized_desc = (desc or "").strip()
    if normalized_desc:
        return normalized_desc
    normalized_reason = (reason or "").strip()
    if normalized_reason:
        return f"{name}：{normalized_reason}"
    if question_excerpt:
        return f"{name}：围绕 {anchor_name} 的候选概念，来源于问题“{question_excerpt}”。"
    return f"{name}：围绕 {anchor_name} 的候选补充概念。"


def _build_missing_anchor_desc(anchor_name: str, question_excerpt: str) -> str:
    if question_excerpt:
        return f"{anchor_name}：当前问题围绕这个核心概念展开，但正式知识图谱里还缺少对应结点。"
    return f"{anchor_name}：当前问题中的核心概念，正式知识图谱里暂未收录。"


def _build_missing_anchor_reason(anchor_name: str) -> str:
    return f"{anchor_name} 是当前问题的核心概念，但正式知识图谱里还没有对应结点，建议教师确认后补充。"


def _load_weak_point_name_map(db: Session) -> dict[int, str | None]:
    weak_rows = db.query(UserWeakPoint).all()
    return {
        row.id: (row.knowledge_node.node_name if row.knowledge_node else None)
        for row in weak_rows
    }


def _parse_json_object(text: str) -> dict | None:
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start:end])
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def _resolve_chat_anchor(question: str, facts: list, keywords: list[str]) -> tuple[str | None, bool]:
    fact_anchor = None
    for fact in facts or []:
        if isinstance(fact, dict) and fact.get("type") == "weak_point" and fact.get("node_name"):
            fact_anchor = str(fact["node_name"]).strip()
            break
    if not fact_anchor:
        for fact in facts or []:
            if isinstance(fact, dict) and fact.get("type") == "selected_path" and fact.get("target"):
                fact_anchor = str(fact["target"]).strip()
                break

    candidate_names = []
    if fact_anchor:
        candidate_names.append(fact_anchor)
    candidate_names.extend(item.strip() for item in keywords if isinstance(item, str) and item.strip())
    if not candidate_names:
        compact = " ".join((question or "").split())
        if compact:
            candidate_names.append(compact.split(" ")[0])
    if not candidate_names:
        return None, False

    existing = _existing_graph_node_names(candidate_names)
    for name in candidate_names:
        if name in existing:
            return name, True
    return candidate_names[0], False


def _pending_batch_node_name_set(
    db: Session,
    *,
    user_id: int | None,
    anchor_name: str,
    source_type: str,
    source_weak_point_id: int | None = None,
) -> set[str]:
    rows = (
        db.query(PendingProposalBatchNode.node_name)
        .join(PendingProposalBatch, PendingProposalBatch.id == PendingProposalBatchNode.batch_id)
        .filter(
            PendingProposalBatch.status == "pending",
            PendingProposalBatch.anchor_name == anchor_name,
            PendingProposalBatch.source_type == source_type,
        )
    )
    if user_id is not None:
        rows = rows.filter(PendingProposalBatch.source_user_id == user_id)
    if source_weak_point_id is not None:
        rows = rows.filter(
            (PendingProposalBatch.source_weak_point_id == source_weak_point_id)
            | (PendingProposalBatch.source_weak_point_id.is_(None))
        )
    return {row[0] for row in rows.all() if row[0]}


def _legacy_pending_name_set(
    db: Session,
    *,
    user_id: int | None,
    anchor_name: str,
    source_weak_point_id: int | None = None,
) -> set[str]:
    proposals = list_pending_proposals_for_anchor(
        db,
        user_id=user_id or 0,
        anchor_node_name=anchor_name,
        source_weak_point_id=source_weak_point_id,
    ) if user_id is not None else []
    return {proposal.name for proposal in proposals if proposal.name}


def create_pending_batch(
    db: Session,
    *,
    source_type: str,
    source_user_id: int | None,
    source_chat_session_id: int | None,
    source_weak_point_id: int | None,
    anchor_name: str,
    anchor_status: str,
    question_excerpt: str,
    nodes: list[dict],
    edges: list[dict],
) -> PendingProposalBatch | None:
    normalized_nodes = []
    seen_names = set()
    for item in nodes:
        name = str(item.get("name") or "").strip()
        if not name or name in seen_names:
            continue
        seen_names.add(name)
        normalized_nodes.append(
            {
                "name": name,
                "desc": _ensure_node_desc(
                    name=name,
                    desc=str(item.get("desc") or "").strip(),
                    reason=str(item.get("reason") or "").strip(),
                    question_excerpt=question_excerpt,
                    anchor_name=anchor_name,
                ),
                "reason": str(item.get("reason") or "").strip(),
                "node_type": (item.get("node_type") or "").strip() or None,
                "is_anchor": bool(item.get("is_anchor")),
                "status": item.get("status") or ("anchor_pending" if item.get("is_anchor") else "pending"),
                "is_selected_default": bool(item.get("is_selected_default", True)),
            }
        )

    if not normalized_nodes:
        return None

    batch = PendingProposalBatch(
        source_type=source_type,
        source_user_id=source_user_id,
        source_chat_session_id=source_chat_session_id,
        source_weak_point_id=source_weak_point_id,
        anchor_name=anchor_name,
        anchor_status=anchor_status,
        question_excerpt=(question_excerpt or "").strip(),
        status="pending",
    )
    db.add(batch)
    db.flush()

    for item in normalized_nodes:
        batch.nodes.append(
            PendingProposalBatchNode(
                node_name=item["name"],
                desc=item["desc"],
                reason=item["reason"],
                node_type=item["node_type"],
                status=item["status"],
                is_anchor=item["is_anchor"],
                is_selected_default=item["is_selected_default"],
                review_state="pending",
            )
        )

    allowed_names = {node["name"] for node in normalized_nodes}
    if anchor_status == "existing":
        allowed_names.add(anchor_name)

    seen_edges = set()
    for item in edges:
        source_name = str(item.get("source") or "").strip()
        target_name = str(item.get("target") or "").strip()
        relation = _normalize_relation(item.get("relation") or "DEPENDS_ON")
        direction = str(item.get("direction") or "out").strip() or "out"
        if not source_name or not target_name:
            continue
        if source_name not in allowed_names or target_name not in allowed_names:
            continue
        edge_key = (source_name, target_name, relation, direction)
        if edge_key in seen_edges:
            continue
        seen_edges.add(edge_key)
        batch.edges.append(
            PendingProposalBatchEdge(
                source_name=source_name,
                target_name=target_name,
                relation=relation,
                direction=direction,
                status="pending",
                is_selected_default=bool(item.get("is_selected_default", True)),
                review_state="pending",
            )
        )

    db.flush()
    return batch


def create_pending_batch_from_candidates(
    db: Session,
    *,
    source_type: str,
    source_user_id: int | None,
    source_chat_session_id: int | None,
    source_weak_point_id: int | None,
    anchor_name: str,
    anchor_status: str,
    question_excerpt: str,
    nodes: list[dict],
    edges: list[dict],
) -> PendingProposalBatch | None:
    # Candidate creation must filter against both Neo4j and all still-pending
    # queues, otherwise repeated chat / weak-page triggers would generate many
    # duplicate review batches for the same anchor concept.
    existing_pending_names = _pending_batch_node_name_set(
        db,
        user_id=source_user_id,
        anchor_name=anchor_name,
        source_type=source_type,
        source_weak_point_id=source_weak_point_id,
    )
    existing_pending_names.update(
        _legacy_pending_name_set(
            db,
            user_id=source_user_id,
            anchor_name=anchor_name,
            source_weak_point_id=source_weak_point_id,
        )
    )
    existing_graph_names = _existing_graph_node_names(
        [anchor_name, *[str(item.get("name") or "").strip() for item in nodes]]
    )

    filtered_nodes = []
    for item in nodes:
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        if name in existing_pending_names:
            continue
        if name in existing_graph_names and not bool(item.get("is_anchor")):
            continue
        filtered_nodes.append(item)

    if anchor_status == "existing":
        filtered_nodes = [item for item in filtered_nodes if str(item.get("name") or "").strip() != anchor_name]

    if not filtered_nodes:
        return None

    allowed_names = {str(item.get("name") or "").strip() for item in filtered_nodes}
    if anchor_status == "existing":
        allowed_names.add(anchor_name)
    filtered_edges = []
    for edge in edges:
        source_name = str(edge.get("source") or "").strip()
        target_name = str(edge.get("target") or "").strip()
        if source_name in allowed_names and target_name in allowed_names:
            filtered_edges.append(edge)

    return create_pending_batch(
        db,
        source_type=source_type,
        source_user_id=source_user_id,
        source_chat_session_id=source_chat_session_id,
        source_weak_point_id=source_weak_point_id,
        anchor_name=anchor_name,
        anchor_status=anchor_status,
        question_excerpt=question_excerpt,
        nodes=filtered_nodes,
        edges=filtered_edges,
    )


def _serialize_batch_summary(
    batch: PendingProposalBatch,
    weak_name_map: dict[int, str | None],
) -> PendingBatchSummaryResponse:
    pending_nodes = [node for node in batch.nodes if node.review_state == "pending"]
    pending_edges = [edge for edge in batch.edges if edge.review_state == "pending"]
    return PendingBatchSummaryResponse(
        id=_batch_public_id(batch.id),
        status=batch.status,
        source_type=batch.source_type,
        anchor_name=batch.anchor_name,
        anchor_status=batch.anchor_status,
        question_excerpt=batch.question_excerpt or "",
        source_weak_point=weak_name_map.get(batch.source_weak_point_id),
        source_user_id=batch.source_user_id,
        source_chat_session_id=batch.source_chat_session_id,
        created_at=batch.created_at,
        pending_node_count=len(pending_nodes),
        pending_edge_count=len(pending_edges),
        node_names=[node.node_name for node in pending_nodes],
    )


def _infer_legacy_anchor_name(proposal: PendingNodeProposal) -> str | None:
    for edge in proposal.suggested_edges:
        if edge.source_name == proposal.name and edge.target_name != proposal.name:
            return edge.target_name
        if edge.target_name == proposal.name and edge.source_name != proposal.name:
            return edge.source_name
    return None


def _serialize_legacy_batch_summary(
    proposal: PendingNodeProposal,
    weak_name_map: dict[int, str | None],
) -> PendingBatchSummaryResponse:
    anchor_name = _infer_legacy_anchor_name(proposal)
    return PendingBatchSummaryResponse(
        id=_legacy_batch_public_id(proposal.id),
        status=proposal.status,
        source_type="legacy",
        anchor_name=anchor_name or proposal.name,
        anchor_status="existing" if anchor_name else "pending",
        question_excerpt=(proposal.reason or proposal.desc or "")[:180],
        source_weak_point=weak_name_map.get(proposal.source_weak_point_id),
        source_user_id=proposal.source_user_id,
        source_chat_session_id=proposal.source_chat_session_id,
        created_at=proposal.created_at,
        pending_node_count=1,
        pending_edge_count=len(proposal.suggested_edges),
        node_names=[proposal.name],
    )


def list_pending_batches(db: Session) -> list[PendingBatchSummaryResponse]:
    weak_name_map = _load_weak_point_name_map(db)
    batch_rows = (
        db.query(PendingProposalBatch)
        .options(joinedload(PendingProposalBatch.nodes), joinedload(PendingProposalBatch.edges))
        .filter(PendingProposalBatch.status == "pending")
        .order_by(PendingProposalBatch.created_at.desc())
        .all()
    )
    legacy_rows = (
        db.query(PendingNodeProposal)
        .options(joinedload(PendingNodeProposal.suggested_edges))
        .filter(PendingNodeProposal.status == "pending")
        .order_by(PendingNodeProposal.created_at.desc())
        .all()
    )
    result = [_serialize_batch_summary(row, weak_name_map) for row in batch_rows]
    result.extend(_serialize_legacy_batch_summary(row, weak_name_map) for row in legacy_rows)
    return result


def _get_pending_batch(db: Session, batch_id: str) -> PendingProposalBatch:
    if not batch_id.startswith("batch:"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending batch not found")
    db_id = batch_id.split(":", 1)[1]
    if not db_id.isdigit():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending batch not found")
    batch = (
        db.query(PendingProposalBatch)
        .options(joinedload(PendingProposalBatch.nodes), joinedload(PendingProposalBatch.edges))
        .filter(PendingProposalBatch.id == int(db_id), PendingProposalBatch.status == "pending")
        .first()
    )
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending batch not found")
    return batch


def _build_batch_detail(
    batch: PendingProposalBatch,
    weak_name_map: dict[int, str | None],
) -> PendingBatchDetailResponse:
    # Teacher review uses a hybrid graph: pending nodes and edges come from
    # MySQL, while already-existing context nodes are fetched from Neo4j so the
    # reviewer can see how the candidate subgraph connects to the formal graph.
    pending_names = {node.node_name for node in batch.nodes}
    context_names = set()
    if batch.anchor_status == "existing" and batch.anchor_name:
        context_names.add(batch.anchor_name)
    for edge in batch.edges:
        if edge.source_name not in pending_names:
            context_names.add(edge.source_name)
        if edge.target_name not in pending_names:
            context_names.add(edge.target_name)
    context_desc_map = _fetch_graph_nodes(context_names)

    graph_nodes: list[PendingBatchGraphNodeResponse] = []
    name_to_graph_id: dict[str, str] = {}
    for node in batch.nodes:
        graph_id = _batch_node_public_id(node.id)
        name_to_graph_id[node.node_name] = graph_id
        graph_nodes.append(
            PendingBatchGraphNodeResponse(
                id=graph_id,
                name=node.node_name,
                desc=node.desc or "",
                reason=node.reason or "",
                status=node.status or ("anchor_pending" if node.is_anchor else "pending"),
                is_anchor=node.is_anchor,
                is_selected_default=node.is_selected_default,
            )
        )

    for name in sorted(context_names):
        if name in pending_names:
            continue
        graph_id = _context_node_public_id(name)
        name_to_graph_id[name] = graph_id
        graph_nodes.append(
            PendingBatchGraphNodeResponse(
                id=graph_id,
                name=name,
                desc=context_desc_map.get(name, ""),
                reason="",
                status="anchor_existing" if name == batch.anchor_name else "context_existing",
                is_anchor=name == batch.anchor_name,
                is_selected_default=False,
            )
        )

    graph_edges: list[PendingBatchGraphEdgeResponse] = []
    for edge in batch.edges:
        source_id = name_to_graph_id.get(edge.source_name)
        target_id = name_to_graph_id.get(edge.target_name)
        if not source_id or not target_id:
            continue
        graph_edges.append(
            PendingBatchGraphEdgeResponse(
                id=_batch_edge_public_id(edge.id),
                source=source_id,
                target=target_id,
                relation=edge.relation,
                status="pending",
                is_selected_default=edge.is_selected_default,
            )
        )

    return PendingBatchDetailResponse(
        batch=PendingBatchDetailBatchResponse(
            id=_batch_public_id(batch.id),
            status=batch.status,
            source_type=batch.source_type,
            anchor_name=batch.anchor_name,
            anchor_status=batch.anchor_status,
            question_excerpt=batch.question_excerpt or "",
            source_weak_point=weak_name_map.get(batch.source_weak_point_id),
            source_user_id=batch.source_user_id,
            source_chat_session_id=batch.source_chat_session_id,
            created_at=batch.created_at,
        ),
        nodes=graph_nodes,
        edges=graph_edges,
    )


def _build_legacy_batch_detail(
    proposal: PendingNodeProposal,
    weak_name_map: dict[int, str | None],
) -> PendingBatchDetailResponse:
    anchor_name = _infer_legacy_anchor_name(proposal)
    context_names = {anchor_name} if anchor_name else set()
    context_desc_map = _fetch_graph_nodes(context_names)
    proposal_node_id = f"pending:{proposal.id}"
    nodes = [
        PendingBatchGraphNodeResponse(
            id=proposal_node_id,
            name=proposal.name,
            desc=proposal.desc or "",
            reason=proposal.reason or "",
            status="pending",
            is_anchor=False,
            is_selected_default=True,
        )
    ]
    name_to_graph_id = {proposal.name: proposal_node_id}
    if anchor_name:
        anchor_id = _context_node_public_id(anchor_name)
        name_to_graph_id[anchor_name] = anchor_id
        nodes.append(
            PendingBatchGraphNodeResponse(
                id=anchor_id,
                name=anchor_name,
                desc=context_desc_map.get(anchor_name, ""),
                reason="",
                status="anchor_existing",
                is_anchor=True,
                is_selected_default=False,
            )
        )

    edges = []
    for edge in proposal.suggested_edges:
        source_id = name_to_graph_id.get(edge.source_name, proposal_node_id if edge.source_name == proposal.name else "")
        target_id = name_to_graph_id.get(edge.target_name, proposal_node_id if edge.target_name == proposal.name else "")
        if not source_id or not target_id:
            continue
        edges.append(
            PendingBatchGraphEdgeResponse(
                id=f"legacy-edge:{edge.id}",
                source=source_id,
                target=target_id,
                relation=edge.relation,
                status="pending",
                is_selected_default=True,
            )
        )

    return PendingBatchDetailResponse(
        batch=PendingBatchDetailBatchResponse(
            id=_legacy_batch_public_id(proposal.id),
            status=proposal.status,
            source_type="legacy",
            anchor_name=anchor_name or proposal.name,
            anchor_status="existing" if anchor_name else "pending",
            question_excerpt=(proposal.reason or proposal.desc or "")[:180],
            source_weak_point=weak_name_map.get(proposal.source_weak_point_id),
            source_user_id=proposal.source_user_id,
            source_chat_session_id=proposal.source_chat_session_id,
            created_at=proposal.created_at,
        ),
        nodes=nodes,
        edges=edges,
    )


def get_pending_batch_detail(db: Session, batch_id: str) -> PendingBatchDetailResponse:
    weak_name_map = _load_weak_point_name_map(db)
    if batch_id.startswith("legacy:"):
        proposal_id = batch_id.split(":", 1)[1]
        if not proposal_id.isdigit():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending batch not found")
        proposal = (
            db.query(PendingNodeProposal)
            .options(joinedload(PendingNodeProposal.suggested_edges))
            .filter(PendingNodeProposal.id == int(proposal_id), PendingNodeProposal.status == "pending")
            .first()
        )
        if not proposal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending batch not found")
        return _build_legacy_batch_detail(proposal, weak_name_map)

    batch = _get_pending_batch(db, batch_id)
    return _build_batch_detail(batch, weak_name_map)


def approve_pending_batch(
    db: Session,
    current_user: User,
    batch_id: str,
    payload: PendingBatchApproveRequest,
) -> dict:
    # Approval is intentionally partial. Teachers may keep only part of a batch,
    # and omitted items stay recorded as review results instead of being forced
    # into Neo4j just because they were proposed together.
    if batch_id.startswith("legacy:"):
        proposal_id = batch_id.split(":", 1)[1]
        if not proposal_id.isdigit():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending batch not found")
        if not payload.nodes:
            reject_pending_proposal(db, current_user, int(proposal_id), PendingNodeRejectRequest(note="omitted"))
            return {"ok": True, "status": "rejected"}
        node = payload.nodes[0]
        legacy_payload = PendingNodeApproveRequest(
            name=node.name,
            desc=node.desc,
            node_type=node.node_type,
            suggested_edges=[
                {
                    "source": edge.source,
                    "target": edge.target,
                    "relation": edge.relation,
                    "direction": "out",
                }
                for edge in payload.edges
            ],
        )
        return approve_pending_proposal(db, current_user, int(proposal_id), legacy_payload)

    batch = _get_pending_batch(db, batch_id)
    selected_nodes = {item.id: item for item in payload.nodes}
    selected_edges = {item.id: item for item in payload.edges}
    if not selected_nodes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one node must be selected")

    graph_driver = GraphDatabase.driver(settings.neo4j_uri, auth=settings.neo4j_auth)
    try:
        with graph_driver.session(database=settings.neo4j_db_name) as session:
            for node in batch.nodes:
                public_id = _batch_node_public_id(node.id)
                if public_id not in selected_nodes:
                    continue
                payload_node = selected_nodes[public_id]
                if not _neo4j_node_exists(session, payload_node.name):
                    session.run(
                        """
                        CREATE (n:Knowledge {name: $name, desc: $desc, node_type: $node_type})
                        """,
                        name=payload_node.name.strip(),
                        desc=(payload_node.desc or "").strip(),
                        node_type=(payload_node.node_type or "").strip(),
                    )

            for edge in batch.edges:
                public_id = _batch_edge_public_id(edge.id)
                if public_id not in selected_edges:
                    continue
                payload_edge = selected_edges[public_id]
                relation = _normalize_relation(payload_edge.relation)
                source_name = payload_edge.source
                target_name = payload_edge.target
                if source_name.startswith("context:"):
                    source_name = source_name.split(":", 1)[1]
                if target_name.startswith("context:"):
                    target_name = target_name.split(":", 1)[1]
                if not _neo4j_node_exists(session, source_name) or not _neo4j_node_exists(session, target_name):
                    continue
                session.run(
                    f"""
                    MATCH (src:Knowledge {{name: $source}})
                    MATCH (tgt:Knowledge {{name: $target}})
                    MERGE (src)-[r:{relation}]->(tgt)
                    """,
                    source=source_name,
                    target=target_name,
                )
    finally:
        graph_driver.close()

    approved_node_ids = set(selected_nodes)
    approved_edge_ids = set(selected_edges)
    for node in batch.nodes:
        node.review_state = "approved" if _batch_node_public_id(node.id) in approved_node_ids else "omitted"
    for edge in batch.edges:
        edge.review_state = "approved" if _batch_edge_public_id(edge.id) in approved_edge_ids else "omitted"

    total_items = len(batch.nodes) + len(batch.edges)
    approved_items = len(approved_node_ids) + len(approved_edge_ids)
    batch.status = "approved" if approved_items == total_items else "partially_approved"
    batch.reviewed_at = datetime.utcnow()
    batch.reviewed_by = current_user.id
    batch.review_note = "approved"
    db.commit()
    return {"ok": True, "status": batch.status}


def reject_pending_batch(
    db: Session,
    current_user: User,
    batch_id: str,
    payload: PendingBatchRejectRequest,
) -> dict:
    if batch_id.startswith("legacy:"):
        proposal_id = batch_id.split(":", 1)[1]
        if not proposal_id.isdigit():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending batch not found")
        return reject_pending_proposal(db, current_user, int(proposal_id), PendingNodeRejectRequest(note=payload.note))

    batch = _get_pending_batch(db, batch_id)
    batch.status = "rejected"
    batch.review_note = (payload.note or "").strip()
    batch.reviewed_at = datetime.utcnow()
    batch.reviewed_by = current_user.id
    for node in batch.nodes:
        node.review_state = "rejected"
    for edge in batch.edges:
        edge.review_state = "rejected"
    db.commit()
    return {"ok": True, "status": batch.status}


def list_pending_batch_nodes_for_anchor(
    db: Session,
    *,
    user_id: int,
    anchor_name: str,
    source_weak_point_id: int | None = None,
) -> list[dict]:
    rows = (
        db.query(PendingProposalBatch)
        .options(joinedload(PendingProposalBatch.nodes), joinedload(PendingProposalBatch.edges))
        .filter(
            PendingProposalBatch.status == "pending",
            PendingProposalBatch.source_user_id == user_id,
            PendingProposalBatch.anchor_name == anchor_name,
        )
        .order_by(PendingProposalBatch.created_at.desc())
        .all()
    )
    if source_weak_point_id is not None:
        rows = [row for row in rows if row.source_weak_point_id == source_weak_point_id or row.source_weak_point_id is None]

    items = []
    seen_ids = set()
    for batch in rows:
        for node in batch.nodes:
            related_edges = []
            for edge in batch.edges:
                if edge.source_name == node.node_name or edge.target_name == node.node_name:
                    related_edges.append(
                        {
                            "source": edge.source_name,
                            "target": edge.target_name,
                            "relation": edge.relation,
                            "direction": edge.direction,
                        }
                    )
            item = {
                "id": _batch_node_public_id(node.id),
                "batch_id": _batch_public_id(batch.id),
                "proposal_id": node.id,
                "name": node.node_name,
                "desc": node.desc or "",
                "status": "pending",
                "reason": node.reason or "",
                "suggested_edges": related_edges,
            }
            items.append(item)
            seen_ids.add(item["id"])

    legacy_rows = list_pending_proposals_for_anchor(
        db,
        user_id=user_id,
        anchor_node_name=anchor_name,
        source_weak_point_id=source_weak_point_id,
    )
    for proposal in legacy_rows:
        serialized = serialize_pending_proposal(proposal)
        if serialized["id"] in seen_ids:
            continue
        items.append(serialized)
    return items


def get_pending_batch_node_context(db: Session, batch_node_id: int, user_id: int | None = None) -> dict | None:
    node = (
        db.query(PendingProposalBatchNode)
        .options(joinedload(PendingProposalBatchNode.batch).joinedload(PendingProposalBatch.edges))
        .filter(PendingProposalBatchNode.id == batch_node_id)
        .first()
    )
    if not node or not node.batch:
        return None
    if user_id is not None and node.batch.source_user_id not in (None, user_id):
        return None

    related_concepts = []
    for edge in node.batch.edges:
        if edge.source_name == node.node_name and edge.target_name != node.node_name:
            related_concepts.append({"name": edge.target_name, "relation": edge.relation})
        elif edge.target_name == node.node_name and edge.source_name != node.node_name:
            related_concepts.append({"name": edge.source_name, "relation": edge.relation})

    return {
        "name": node.node_name,
        "desc": node.desc or node.reason or "",
        "related_concepts": related_concepts[:5],
        "is_pending": True,
    }


def get_pending_node_context(db: Session, node_id: str, user_id: int | None = None) -> dict | None:
    if isinstance(node_id, str) and node_id.startswith("pending-batch-node:"):
        raw_id = node_id.split(":", 1)[1]
        if raw_id.isdigit():
            context = get_pending_batch_node_context(db, int(raw_id), user_id=user_id)
            if context:
                return context
    if isinstance(node_id, str) and node_id.startswith("pending:"):
        raw_id = node_id.split(":", 1)[1]
        if raw_id.isdigit():
            return get_pending_proposal_context(db, int(raw_id), user_id)
    return None


def _normalize_batch_edges(
    edges: list[dict],
    *,
    allowed_names: set[str],
    anchor_name: str,
    anchor_status: str,
) -> list[dict]:
    normalized = []
    seen = set()
    for edge in edges:
        source_name = str(edge.get("source") or "").strip()
        target_name = str(edge.get("target") or "").strip()
        if not source_name or not target_name:
            continue
        if source_name not in allowed_names or target_name not in allowed_names:
            continue
        key = (source_name, target_name, "DEPENDS_ON")
        if key in seen:
            continue
        seen.add(key)
        normalized.append(
            {
                "source": source_name,
                "target": target_name,
                "relation": "DEPENDS_ON",
                "direction": str(edge.get("direction") or "out").strip() or "out",
            }
        )

    if normalized:
        return normalized

    node_names = [name for name in allowed_names if name != anchor_name]
    return [
        {
            "source": node_name,
            "target": anchor_name,
            "relation": "DEPENDS_ON",
            "direction": "out",
        }
        for node_name in node_names
        if anchor_status == "existing" or anchor_name in allowed_names
    ]


def _keyword_batch_fallback(
    *,
    anchor_name: str,
    anchor_exists: bool,
    question: str,
    keywords: list[str],
    max_nodes: int,
    excluded_names: set[str],
) -> tuple[list[dict], list[dict]]:
    # This fallback keeps the review path alive even when graph recall is empty
    # or the LLM fails to return valid JSON for the batch proposal.
    question_excerpt = _build_question_excerpt(question)
    nodes = []
    seen_names = set(excluded_names)
    if not anchor_exists and anchor_name and anchor_name not in seen_names:
        nodes.append(
            {
                "name": anchor_name,
                "desc": _build_missing_anchor_desc(anchor_name, question_excerpt),
                "reason": _build_missing_anchor_reason(anchor_name),
                "is_anchor": True,
                "status": "anchor_pending",
            }
        )
        seen_names.add(anchor_name)

    for keyword in keywords:
        name = str(keyword or "").strip()
        if not name or name in seen_names:
            continue
        nodes.append(
            {
                "name": name,
                "desc": _ensure_node_desc(
                    name=name,
                    desc="",
                    reason=f"该概念直接出现在问题中，适合作为围绕 {anchor_name} 的候选补充知识点。",
                    question_excerpt=question_excerpt,
                    anchor_name=anchor_name,
                ),
                "reason": f"该概念直接出现在问题中，适合作为围绕 {anchor_name} 的候选补充知识点。",
                "is_anchor": False,
                "status": "pending",
            }
        )
        seen_names.add(name)
        if len(nodes) >= max_nodes:
            break

    allowed_names = {node["name"] for node in nodes}
    if anchor_exists:
        allowed_names.add(anchor_name)
    edges = _normalize_batch_edges(
        [
            {
                "source": node["name"],
                "target": anchor_name,
                "relation": "DEPENDS_ON",
                "direction": "out",
            }
            for node in nodes
            if node["name"] != anchor_name
        ],
        allowed_names=allowed_names,
        anchor_name=anchor_name,
        anchor_status="existing" if anchor_exists else "pending",
    )
    return nodes, edges


def propose_pending_batch_from_chat(
    db: Session,
    *,
    question: str,
    facts: list,
    keywords: list[str] | None,
    user_id: int,
    session_id: int | None = None,
) -> dict | None:
    # Chat proposals are model-assisted but still guarded locally: anchor
    # resolution, duplicate filtering, and fallback batch assembly all happen in
    # service code so the queue remains stable even with imperfect LLM output.
    normalized_keywords = [item.strip() for item in (keywords or []) if isinstance(item, str) and item.strip()]
    anchor_name, anchor_exists = _resolve_chat_anchor(question, facts, normalized_keywords)
    if not anchor_name:
        return None

    question_excerpt = _build_question_excerpt(question)
    max_nodes = 5 if not facts else 4
    existing_graph_names = _existing_graph_node_names([anchor_name, *normalized_keywords])
    already_pending_names = _pending_batch_node_name_set(
        db,
        user_id=user_id,
        anchor_name=anchor_name,
        source_type="chat",
    )
    already_pending_names.update(
        _legacy_pending_name_set(
            db,
            user_id=user_id,
            anchor_name=anchor_name,
        )
    )
    if anchor_exists:
        already_pending_names.add(anchor_name)
    excluded_names = set(existing_graph_names) | set(already_pending_names)

    client = OpenAI(api_key=settings.llm_api_key or None, base_url=settings.llm_base_url)
    prompt = f"""
你是知识图谱扩展助手。请围绕当前锚点知识点输出一个候选知识子图批次。

要求：
1. 只返回一个 JSON 对象。
2. anchor 必须是当前锚点 {anchor_name}。
3. 最多提供 {max_nodes} 个待审结点。
4. 每个结点都必须提供 name、desc、reason。
5. edges 只允许使用 DEPENDS_ON。
6. 不要返回这些已存在的正式图谱结点：{json.dumps(sorted(existing_graph_names), ensure_ascii=False)}
7. 不要返回这些已存在的待审核结点：{json.dumps(sorted(already_pending_names), ensure_ascii=False)}
8. 如果没有合适候选，请返回空数组 nodes。

用户问题：
{question}

已有事实摘要：
{json.dumps([fact for fact in facts if isinstance(fact, dict)][:8], ensure_ascii=False)}

关键词：
{json.dumps(normalized_keywords, ensure_ascii=False)}

返回格式：
{{
  "anchor": {{
    "name": "{anchor_name}",
    "exists_in_graph": {str(anchor_exists).lower()},
    "desc": "如果锚点不在正式图谱中，请给出锚点的概念描述；若已存在则可留空",
    "reason": "如果锚点不在正式图谱中，请说明为什么它值得补充入图；若已存在则可留空"
  }},
  "nodes": [
    {{
      "name": "候选结点名",
      "desc": "候选描述",
      "reason": "推荐原因",
      "is_anchor": false
    }}
  ],
  "edges": [
    {{
      "source": "候选结点名",
      "target": "{anchor_name}",
      "relation": "DEPENDS_ON",
      "direction": "out"
    }}
  ]
}}
"""

    parsed = None
    try:
        response = client.chat.completions.create(
            model=settings.llm_model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        parsed = _parse_json_object(response.choices[0].message.content or "")
    except Exception:
        parsed = None

    nodes: list[dict] = []
    edges: list[dict] = []
    if parsed:
        raw_anchor = parsed.get("anchor") if isinstance(parsed.get("anchor"), dict) else {}
        raw_nodes = parsed.get("nodes") if isinstance(parsed.get("nodes"), list) else []
        seen_names = set(excluded_names)
        if not anchor_exists and anchor_name not in seen_names:
            anchor_reason = str(raw_anchor.get("reason") or "").strip()
            nodes.append(
                {
                    "name": anchor_name,
                    "desc": _ensure_node_desc(
                        name=anchor_name,
                        desc=str(raw_anchor.get("desc") or "").strip(),
                        reason=anchor_reason,
                        question_excerpt=question_excerpt,
                        anchor_name=anchor_name,
                    ),
                    "reason": anchor_reason or _build_missing_anchor_reason(anchor_name),
                    "is_anchor": True,
                    "status": "anchor_pending",
                }
            )
            seen_names.add(anchor_name)

        for item in raw_nodes:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name or name in seen_names:
                continue
            nodes.append(
                {
                    "name": name,
                    "desc": _ensure_node_desc(
                        name=name,
                        desc=str(item.get("desc") or "").strip(),
                        reason=str(item.get("reason") or "").strip(),
                        question_excerpt=question_excerpt,
                        anchor_name=anchor_name,
                    ),
                    "reason": str(item.get("reason") or "").strip(),
                    "is_anchor": bool(item.get("is_anchor")),
                    "status": "pending",
                }
            )
            seen_names.add(name)
            if len(nodes) >= max_nodes:
                break

        allowed_names = {node["name"] for node in nodes}
        if anchor_exists:
            allowed_names.add(anchor_name)
        raw_edges = parsed.get("edges") if isinstance(parsed.get("edges"), list) else []
        edges = _normalize_batch_edges(
            raw_edges,
            allowed_names=allowed_names,
            anchor_name=anchor_name,
            anchor_status="existing" if anchor_exists else "pending",
        )

    if not nodes:
        nodes, edges = _keyword_batch_fallback(
            anchor_name=anchor_name,
            anchor_exists=anchor_exists,
            question=question,
            keywords=normalized_keywords,
            max_nodes=max_nodes,
            excluded_names=excluded_names,
        )

    batch = create_pending_batch_from_candidates(
        db,
        source_type="chat",
        source_user_id=user_id,
        source_chat_session_id=session_id,
        source_weak_point_id=None,
        anchor_name=anchor_name,
        anchor_status="existing" if anchor_exists else "pending",
        question_excerpt=question_excerpt,
        nodes=nodes,
        edges=edges,
    )
    if not batch:
        return None

    db.commit()
    pending_names = [node.node_name for node in batch.nodes]
    return {
        "batch_id": _batch_public_id(batch.id),
        "anchor_name": anchor_name,
        "node_names": pending_names,
        "pending_nodes": [
            {
                "proposal_id": node.id,
                "name": node.node_name,
                "desc": node.desc,
                "reason": node.reason,
                "status": node.status,
            }
            for node in batch.nodes
        ],
        "message": f"系统发现当前图谱可能缺少知识子图【{'、'.join(pending_names)}】，已提交教师审核，稍后可在薄弱点页继续查看。",
    }
