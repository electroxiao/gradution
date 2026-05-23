from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.user import User
from backend.services.knowledge_progress_service import (
    build_graph_state_map,
    get_graph_node_color,
    list_unmastered_weak_point_rows,
)
from backend.services.neo4j_service import get_neo4j_driver

DB_NAME = settings.neo4j_db_name

RECOMMENDATION_STATUS_COLOR_MAP = {
    "weak": "#ef4444",
    "recommended": "#2563eb",
    "mastered": "#22c55e",
    "unknown": "#94a3b8",
}


def _load_target_weak_point(db: Session, user: User, weak_point_id: int | None):
    rows = list_unmastered_weak_point_rows(db, user)
    if not rows:
        return None, None, rows

    if weak_point_id is None:
        return rows[0][0], rows[0][1], rows

    for weak_point, node in rows:
        if node.id == weak_point_id:
            return weak_point, node, rows

    return None, None, rows


def _query_node_details(session, node_name: str) -> dict:
    query = """
    MATCH (n:Knowledge {name: $node_name})
    RETURN n.name AS name, coalesce(n.desc, '') AS desc, labels(n) AS labels
    LIMIT 1
    """
    record = session.run(query, node_name=node_name).single()
    if not record:
        return {"id": node_name, "name": node_name, "desc": "", "labels": []}
    return {
        "id": record["name"],
        "name": record["name"],
        "desc": record["desc"] or "",
        "labels": record["labels"] or [],
    }


def _query_candidate_nodes(session, target_name: str, target_desc: str, limit: int = 6) -> list[dict]:
    candidates: dict[str, dict] = {}

    neighbor_query = """
    MATCH (target:Knowledge {name: $target_name})-[r:DEPENDS_ON]-(neighbor:Knowledge)
    RETURN DISTINCT
        neighbor.name AS name,
        coalesce(neighbor.desc, '') AS desc,
        labels(neighbor) AS labels,
        type(r) AS relation,
        CASE WHEN startNode(r) = target THEN 'out' ELSE 'in' END AS direction
    LIMIT $limit
    """
    for record in session.run(neighbor_query, target_name=target_name, limit=max(limit, 4)):
        name = record["name"]
        if not name or name == target_name:
            continue
        candidates[name] = {
            "id": name,
            "name": name,
            "desc": record["desc"] or "",
            "labels": record["labels"] or [],
            "relation": record["relation"] or "DEPENDS_ON",
            "direction": record["direction"] or "",
            "source": "dependency",
        }

    if len(candidates) >= limit:
        return list(candidates.values())[:limit]

    keyword_terms = [term for term in {target_name, *(target_name.split()), *(target_desc.split())} if term][:4]
    if keyword_terms:
        keyword_query = """
        MATCH (n:Knowledge)
        WHERE n.name <> $target_name
          AND (
            any(term IN $terms WHERE toLower(n.name) CONTAINS toLower(term))
            OR any(term IN $terms WHERE toLower(coalesce(n.desc, '')) CONTAINS toLower(term))
          )
        RETURN DISTINCT n.name AS name, coalesce(n.desc, '') AS desc, labels(n) AS labels
        LIMIT $limit
        """
        for record in session.run(keyword_query, target_name=target_name, terms=keyword_terms, limit=limit * 2):
            name = record["name"]
            if not name or name == target_name or name in candidates:
                continue
            candidates[name] = {
                "id": name,
                "name": name,
                "desc": record["desc"] or "",
                "labels": record["labels"] or [],
                "relation": None,
                "direction": "",
                "source": "keyword",
            }

    return list(candidates.values())[:limit]


def _query_edges_for_nodes(session, node_names: list[str]) -> list[dict]:
    if len(node_names) < 2:
        return []

    query = """
    MATCH (a:Knowledge)-[r:DEPENDS_ON]->(b:Knowledge)
    WHERE a.name IN $node_names AND b.name IN $node_names
    RETURN DISTINCT a.name AS source, b.name AS target, type(r) AS relation
    """
    rows = []
    seen = set()
    for record in session.run(query, node_names=node_names):
        edge_id = f"{record['source']}-{record['relation']}-{record['target']}"
        if edge_id in seen:
            continue
        seen.add(edge_id)
        rows.append(
            {
                "id": edge_id,
                "source": record["source"],
                "target": record["target"],
                "relation": record["relation"] or "DEPENDS_ON",
            }
        )
    return rows


def _build_recommendation_fallback(target_name: str, candidates: list[dict]) -> dict:
    dependency_candidates = [item for item in candidates if item.get("source") == "dependency"]
    keyword_candidates = [item for item in candidates if item.get("source") == "keyword"]
    ranked = dependency_candidates + keyword_candidates
    ranked = ranked[:3]
    recommended_ids = [item["id"] for item in ranked]
    learning_order = recommended_ids + [target_name]

    reasons = {}
    for item in ranked:
        if item.get("source") == "dependency":
            reasons[item["id"]] = "这是当前薄弱点周围最直接的依赖概念，优先补齐通常更有帮助。"
        else:
            reasons[item["id"]] = "这个节点与当前薄弱点在名称或描述上高度相关，适合作为补充复习内容。"

    return {
        "recommended_node_ids": recommended_ids,
        "learning_order": learning_order,
        "summary": f"建议先复习 {', '.join(recommended_ids)}，再回到 {target_name} 做针对性训练。" if recommended_ids else f"当前优先围绕 {target_name} 做针对性训练。",
        "reasons": reasons,
    }


def _recommend_nodes(target: dict, candidates: list[dict], state_map: dict[str, str]) -> dict:
    fallback = _build_recommendation_fallback(target["name"], candidates)
    if not candidates:
        return fallback

    def score(item: dict) -> tuple[int, int, str]:
        status = state_map.get(item["id"], "unknown")
        source_score = 0 if item.get("source") == "dependency" else 1
        status_score = 1 if status == "mastered" else 0
        direction_score = 0 if item.get("direction") == "in" else 1
        return (status_score, source_score, direction_score, item["id"])

    ranked = sorted(candidates, key=score)[:3]
    recommended_ids = [item["id"] for item in ranked]
    learning_order = recommended_ids + [target["id"]]

    reasons = {}
    for item in ranked:
        if state_map.get(item["id"]) == "mastered":
            reasons[item["id"]] = "这个节点你已经掌握，可作为回顾支点，帮助衔接当前薄弱点。"
        elif item.get("source") == "dependency":
            reasons[item["id"]] = "它与当前薄弱点存在直接依赖关系，先补齐更利于理解后续内容。"
        else:
            reasons[item["id"]] = "它与当前薄弱点在名称或描述上相关，适合作为补充复习内容。"

    return {
        "recommended_node_ids": recommended_ids,
        "learning_order": learning_order,
        "summary": f"建议先复习 {', '.join(recommended_ids)}，再回到 {target['name']} 做针对性训练。",
        "reasons": reasons,
    }


def _select_path_edges(all_edges: list[dict], ordered_node_ids: list[str]) -> list[dict]:
    if len(ordered_node_ids) < 2:
        return []

    selected = []
    edge_map = {(edge["source"], edge["target"]): edge for edge in all_edges}
    for source, target in zip(ordered_node_ids, ordered_node_ids[1:]):
        edge = edge_map.get((source, target)) or edge_map.get((target, source))
        if edge:
            selected.append(edge)
    return selected


def _resolve_recommendation_status(node_id: str, target_id: str, state_map: dict[str, str]) -> str:
    if node_id == target_id:
        return "weak"
    if state_map.get(node_id) == "mastered":
        return "mastered"
    return "recommended"


def get_weak_points_graph(db: Session, user: User, weak_point_id: int | None = None) -> dict:
    weak_point, target_node, weak_rows = _load_target_weak_point(db, user, weak_point_id)
    if not weak_rows or not weak_point or not target_node:
        return {
            "target": None,
            "recommended_nodes": [],
            "learning_order": [],
            "summary": "",
            "nodes": [],
            "edges": [],
        }

    state_map = build_graph_state_map(db, user, weak_rows=weak_rows)
    driver = get_neo4j_driver()

    with driver.session(database=DB_NAME) as session:
        target = _query_node_details(session, target_node.node_name)
        candidates = _query_candidate_nodes(session, target["name"], target.get("desc", ""))
        recommendation = _recommend_nodes(target, candidates, state_map)

        recommended_ids = recommendation["recommended_node_ids"]
        selected_node_ids = []
        for node_id in [*recommended_ids, target["id"]]:
            if node_id not in selected_node_ids:
                selected_node_ids.append(node_id)

        node_details_map = {target["id"]: target}
        for candidate in candidates:
            if candidate["id"] in selected_node_ids:
                node_details_map[candidate["id"]] = candidate

        all_edges = _query_edges_for_nodes(session, selected_node_ids)
        graph_edges = _select_path_edges(all_edges, recommendation["learning_order"])

    graph_nodes = []
    recommended_nodes = []
    for node_id in selected_node_ids:
        detail = node_details_map.get(node_id, {"id": node_id, "name": node_id, "desc": ""})
        status = _resolve_recommendation_status(node_id, target["id"], state_map)
        graph_node = {
            "id": detail["id"],
            "name": detail["name"],
            "desc": detail.get("desc", ""),
            "status": status,
            "color": RECOMMENDATION_STATUS_COLOR_MAP.get(status, get_graph_node_color(status)),
        }
        graph_nodes.append(graph_node)
        if node_id != target["id"]:
            recommended_nodes.append(
                {
                    "id": detail["id"],
                    "name": detail["name"],
                    "status": status,
                    "reason": recommendation["reasons"].get(node_id, ""),
                }
            )

    learning_order = []
    for node_id in recommendation["learning_order"]:
        if node_id == target["id"]:
            learning_order.append(target["name"])
        elif node_id in node_details_map:
            learning_order.append(node_details_map[node_id]["name"])

    return {
        "target": {
            "id": target["id"],
            "name": target["name"],
            "status": "weak",
            "weak_point_id": weak_point.id,
        },
        "recommended_nodes": recommended_nodes,
        "learning_order": learning_order,
        "summary": recommendation["summary"],
        "nodes": graph_nodes,
        "edges": graph_edges,
    }
