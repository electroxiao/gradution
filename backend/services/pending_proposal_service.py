from datetime import datetime

from fastapi import HTTPException, status
from neo4j import GraphDatabase
from openai import OpenAI
from sqlalchemy.orm import Session, joinedload

from backend.core.config import settings
from backend.models.knowledge import PendingNodeProposal, PendingNodeProposalEdge, UserWeakPoint
from backend.models.user import User
from backend.schemas.teacher import (
    PendingNodeApproveRequest,
    PendingNodeProposalEdgeResponse,
    PendingNodeProposalResponse,
    PendingNodeRejectRequest,
)


def _ensure_node_exists(session, node_name: str) -> None:
    row = session.run(
        "MATCH (n:Knowledge {name: $name}) RETURN n.name AS name LIMIT 1",
        name=node_name,
    ).single()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node not found: {node_name}",
        )


def _normalize_relation(relation: str) -> str:
    normalized = (relation or "DEPENDS_ON").strip().upper().replace(" ", "_")
    if not normalized or not normalized.replace("_", "").isalnum() or not normalized[0].isalpha():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid relation name")
    return normalized


def create_or_reuse_pending_proposal(
    db: Session,
    *,
    name: str,
    desc: str = "",
    node_type: str | None = None,
    reason: str = "",
    source_weak_point_id: int | None = None,
    source_user_id: int | None = None,
    source_chat_session_id: int | None = None,
    anchor_node_name: str | None = None,
    suggested_edges: list[dict] | None = None,
) -> PendingNodeProposal:
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Proposal name cannot be empty")

    proposals = (
        db.query(PendingNodeProposal)
        .options(joinedload(PendingNodeProposal.suggested_edges))
        .filter(
            PendingNodeProposal.name == normalized_name,
            PendingNodeProposal.status == "pending",
            PendingNodeProposal.source_user_id == source_user_id,
        )
        .order_by(PendingNodeProposal.created_at.desc())
        .all()
    )
    proposal = next(
        (
            item
            for item in proposals
            if _proposal_matches_anchor(item, source_weak_point_id, anchor_node_name)
        ),
        None,
    )
    if proposal:
        if desc and not proposal.desc:
            proposal.desc = desc.strip()
        if reason and not proposal.reason:
            proposal.reason = reason.strip()
        if node_type and not proposal.node_type:
            proposal.node_type = node_type.strip()
        _merge_suggested_edges(proposal, suggested_edges or [])
        db.flush()
        return proposal

    proposal = PendingNodeProposal(
        name=normalized_name,
        desc=(desc or "").strip(),
        node_type=(node_type or "").strip() or None,
        status="pending",
        source_weak_point_id=source_weak_point_id,
        source_user_id=source_user_id,
        source_chat_session_id=source_chat_session_id,
        reason=(reason or "").strip(),
    )
    db.add(proposal)
    db.flush()
    _merge_suggested_edges(proposal, suggested_edges or [])
    db.flush()
    return proposal


def list_pending_proposals_for_anchor(
    db: Session,
    *,
    user_id: int,
    anchor_node_name: str,
    source_weak_point_id: int | None = None,
) -> list[PendingNodeProposal]:
    proposals = (
        db.query(PendingNodeProposal)
        .options(joinedload(PendingNodeProposal.suggested_edges))
        .filter(
            PendingNodeProposal.status == "pending",
            PendingNodeProposal.source_user_id == user_id,
        )
        .order_by(PendingNodeProposal.created_at.desc())
        .all()
    )
    return [
        proposal
        for proposal in proposals
        if _proposal_matches_anchor(proposal, source_weak_point_id, anchor_node_name)
    ]


def serialize_pending_proposal(proposal: PendingNodeProposal) -> dict:
    return {
        "id": f"pending:{proposal.id}",
        "proposal_id": proposal.id,
        "name": proposal.name,
        "desc": proposal.desc or "",
        "status": proposal.status,
        "reason": proposal.reason or "",
        "suggested_edges": [
            {
                "source": edge.source_name,
                "target": edge.target_name,
                "relation": edge.relation,
                "direction": edge.direction,
            }
            for edge in proposal.suggested_edges
        ],
    }


def get_pending_proposal_context(db: Session, proposal_id: int, user_id: int | None = None) -> dict | None:
    proposal = (
        db.query(PendingNodeProposal)
        .options(joinedload(PendingNodeProposal.suggested_edges))
        .filter(PendingNodeProposal.id == proposal_id)
        .first()
    )
    if not proposal:
        return None
    if user_id is not None and proposal.source_user_id not in (None, user_id):
        return None
    related_concepts = []
    for edge in proposal.suggested_edges:
        if edge.source_name != proposal.name:
            related_concepts.append({"name": edge.source_name, "relation": edge.relation})
        if edge.target_name != proposal.name:
            related_concepts.append({"name": edge.target_name, "relation": edge.relation})
    return {
        "name": proposal.name,
        "desc": proposal.desc or proposal.reason or "",
        "related_concepts": related_concepts[:5],
        "is_pending": proposal.status == "pending",
    }


def propose_pending_from_chat(
    db: Session,
    *,
    question: str,
    facts: list,
    user_id: int,
    session_id: int | None = None,
) -> dict | None:
    anchor_node_name = _extract_anchor_node_name(facts)
    if not anchor_node_name:
        return None

    if list_pending_proposals_for_anchor(
        db,
        user_id=user_id,
        anchor_node_name=anchor_node_name,
        source_weak_point_id=None,
    ):
        return None

    selected_path = next(
        (fact for fact in facts if isinstance(fact, dict) and fact.get("type") == "selected_path"),
        None,
    )
    weak_points = [
        fact.get("node_name")
        for fact in facts
        if isinstance(fact, dict) and fact.get("type") == "weak_point" and fact.get("node_name")
    ]
    existing_fact_text = [
        fact.get("path_text") or fact.get("text") or fact.get("node_name") or ""
        for fact in facts
        if isinstance(fact, dict)
    ][:8]

    client = OpenAI(api_key=settings.llm_api_key or None, base_url=settings.llm_base_url)
    prompt = f"""
你是知识图谱扩展助手。请根据用户问题和当前检索到的图谱证据，判断是否需要补充一个待教师审核的新知识结点。

要求：
1. 只有在当前图谱明显缺少关键中间概念时才提议。
2. 最多提议 1 个候选新结点。
3. 候选结点必须围绕锚点知识点 {anchor_node_name}。
4. suggested_edges 只允许使用 DEPENDS_ON。
5. 如果没有必要，返回 []。
6. 只返回 JSON 数组。

用户问题：
{question}

当前主薄弱点 / 锚点：
{anchor_node_name}

当前薄弱点列表：
{json.dumps(weak_points, ensure_ascii=False)}

已选路径：
{selected_path.get('path_text', '') if isinstance(selected_path, dict) else ''}

已有证据摘要：
{json.dumps(existing_fact_text, ensure_ascii=False)}

返回格式：
[
  {{
    "name": "候选结点名",
    "desc": "候选结点描述",
    "reason": "为什么它是当前缺失的关键概念",
    "suggested_edges": [
      {{"source": "候选结点名", "target": "{anchor_node_name}", "relation": "DEPENDS_ON", "direction": "out"}}
    ]
  }}
]
"""
    try:
        response = client.chat.completions.create(
            model=settings.llm_model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        content = response.choices[0].message.content or ""
        start = content.find("[")
        end = content.rfind("]") + 1
        if start == -1 or end <= start:
            return None
        parsed = json.loads(content[start:end])
        if not isinstance(parsed, list) or not parsed:
            return None
        item = parsed[0]
        if not isinstance(item, dict):
            return None
        proposal_name = str(item.get("name") or "").strip()
        if not proposal_name or proposal_name == anchor_node_name:
            return None
        raw_edges = item.get("suggested_edges") if isinstance(item.get("suggested_edges"), list) else []
        suggested_edges = []
        for edge in raw_edges:
            if not isinstance(edge, dict):
                continue
            source = str(edge.get("source") or "").strip() or proposal_name
            target = str(edge.get("target") or "").strip() or anchor_node_name
            suggested_edges.append(
                {
                    "source": source,
                    "target": target,
                    "relation": "DEPENDS_ON",
                    "direction": str(edge.get("direction") or "out").strip() or "out",
                }
            )
        if not suggested_edges:
            suggested_edges = [
                {
                    "source": proposal_name,
                    "target": anchor_node_name,
                    "relation": "DEPENDS_ON",
                    "direction": "out",
                }
            ]

        proposal = create_or_reuse_pending_proposal(
            db,
            name=proposal_name,
            desc=str(item.get("desc") or "").strip(),
            node_type="",
            reason=str(item.get("reason") or "").strip(),
            source_user_id=user_id,
            source_chat_session_id=session_id,
            anchor_node_name=anchor_node_name,
            suggested_edges=suggested_edges,
        )
        db.commit()
        return {
            "anchor_node_name": anchor_node_name,
            "pending_nodes": [serialize_pending_proposal(proposal)],
            "message": f"系统发现当前图谱可能缺少知识点【{proposal.name}】，已提交教师审核，稍后可在薄弱点页继续查看。",
        }
    except Exception:
        db.rollback()
        return None


def list_pending_proposals(db: Session) -> list[PendingNodeProposalResponse]:
    rows = (
        db.query(PendingNodeProposal)
        .options(joinedload(PendingNodeProposal.suggested_edges))
        .filter(PendingNodeProposal.status == "pending")
        .order_by(PendingNodeProposal.created_at.desc())
        .all()
    )
    weak_point_ids = [row.source_weak_point_id for row in rows if row.source_weak_point_id]
    weak_name_map = {}
    if weak_point_ids:
        weak_rows = (
            db.query(UserWeakPoint)
            .filter(UserWeakPoint.id.in_(weak_point_ids))
            .all()
        )
        weak_name_map = {
            row.id: (row.knowledge_node.node_name if row.knowledge_node else None)
            for row in weak_rows
        }

    return [
        PendingNodeProposalResponse(
            id=row.id,
            name=row.name,
            desc=row.desc or "",
            node_type=row.node_type or "",
            reason=row.reason or "",
            status=row.status,
            source_weak_point=weak_name_map.get(row.source_weak_point_id),
            source_user_id=row.source_user_id,
            source_chat_session_id=row.source_chat_session_id,
            created_at=row.created_at,
            suggested_edges=[
                PendingNodeProposalEdgeResponse(
                    id=edge.id,
                    source=edge.source_name,
                    target=edge.target_name,
                    relation=edge.relation,
                    direction=edge.direction,
                )
                for edge in row.suggested_edges
            ],
        )
        for row in rows
    ]


def approve_pending_proposal(
    db: Session,
    current_user: User,
    proposal_id: int,
    payload: PendingNodeApproveRequest,
) -> dict:
    proposal = _get_pending_proposal(db, proposal_id)
    driver = GraphDatabase.driver(settings.neo4j_uri, auth=settings.neo4j_auth)
    node_name = payload.name.strip()

    try:
        with driver.session(database=settings.neo4j_db_name) as session:
            existing = session.run(
                "MATCH (n:Knowledge {name: $name}) RETURN n.name AS name LIMIT 1",
                name=node_name,
            ).single()

            if not existing:
                session.run(
                    """
                    CREATE (n:Knowledge {name: $name, desc: $desc, node_type: $node_type})
                    """,
                    name=node_name,
                    desc=(payload.desc or "").strip(),
                    node_type=(payload.node_type or "").strip(),
                )

            for edge in payload.suggested_edges:
                relation = _normalize_relation(edge.relation)
                source_name = edge.source.strip()
                target_name = edge.target.strip()
                _ensure_node_exists(session, source_name if edge.direction != "in" else target_name)
                _ensure_node_exists(session, target_name if edge.direction != "in" else source_name)
                if edge.direction == "in":
                    source_name, target_name = target_name, source_name

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
        driver.close()

    proposal.status = "approved"
    proposal.name = node_name
    proposal.desc = (payload.desc or "").strip()
    proposal.node_type = (payload.node_type or "").strip() or None
    proposal.reviewed_at = datetime.utcnow()
    proposal.reviewed_by = current_user.id
    proposal.review_note = "approved"
    _replace_suggested_edges(proposal, payload.suggested_edges)
    db.commit()
    return {"ok": True, "status": proposal.status}


def reject_pending_proposal(
    db: Session,
    current_user: User,
    proposal_id: int,
    payload: PendingNodeRejectRequest,
) -> dict:
    proposal = _get_pending_proposal(db, proposal_id)
    proposal.status = "rejected"
    proposal.review_note = (payload.note or "").strip()
    proposal.reviewed_at = datetime.utcnow()
    proposal.reviewed_by = current_user.id
    db.commit()
    return {"ok": True, "status": proposal.status}


def _get_pending_proposal(db: Session, proposal_id: int) -> PendingNodeProposal:
    proposal = (
        db.query(PendingNodeProposal)
        .options(joinedload(PendingNodeProposal.suggested_edges))
        .filter(PendingNodeProposal.id == proposal_id, PendingNodeProposal.status == "pending")
        .first()
    )
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending proposal not found")
    return proposal


def _merge_suggested_edges(proposal: PendingNodeProposal, suggested_edges: list[dict]) -> None:
    existing_keys = {
        (edge.source_name, edge.target_name, edge.relation, edge.direction)
        for edge in proposal.suggested_edges
    }
    for item in suggested_edges:
        source_name = (item.get("source") or "").strip()
        target_name = (item.get("target") or "").strip()
        relation = _normalize_relation(item.get("relation") or "DEPENDS_ON")
        direction = (item.get("direction") or "out").strip() or "out"
        key = (source_name, target_name, relation, direction)
        if not source_name or not target_name or key in existing_keys:
            continue
        proposal.suggested_edges.append(
            PendingNodeProposalEdge(
                source_name=source_name,
                target_name=target_name,
                relation=relation,
                direction=direction,
            )
        )
        existing_keys.add(key)


def _replace_suggested_edges(proposal: PendingNodeProposal, suggested_edges) -> None:
    proposal.suggested_edges.clear()
    for item in suggested_edges:
        proposal.suggested_edges.append(
            PendingNodeProposalEdge(
                source_name=item.source.strip(),
                target_name=item.target.strip(),
                relation=_normalize_relation(item.relation),
                direction=(item.direction or "out").strip() or "out",
            )
        )


def _proposal_matches_anchor(
    proposal: PendingNodeProposal,
    source_weak_point_id: int | None,
    anchor_node_name: str | None,
) -> bool:
    if source_weak_point_id and proposal.source_weak_point_id == source_weak_point_id:
        return True
    if not anchor_node_name:
        return False
    for edge in proposal.suggested_edges:
        if edge.source_name == anchor_node_name or edge.target_name == anchor_node_name:
            return True
    return False


def _extract_anchor_node_name(facts: list) -> str | None:
    for fact in facts or []:
        if isinstance(fact, dict) and fact.get("type") == "weak_point" and fact.get("node_name"):
            return str(fact["node_name"]).strip()
    for fact in facts or []:
        if isinstance(fact, dict) and fact.get("type") == "selected_path" and fact.get("target"):
            return str(fact["target"]).strip()
    return None
