from neo4j import GraphDatabase
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.knowledge import KnowledgeNode, UserWeakPoint
from backend.models.knowledge_state import UserKnowledgeState
from backend.models.user import User
from backend.services.weak_point_service import set_knowledge_state_status

NEO4J_URI = settings.neo4j_uri
NEO4J_AUTH = settings.neo4j_auth
DB_NAME = settings.neo4j_db_name


def list_unmastered_weak_node_names(db: Session, user: User) -> list[str]:
    rows = (
        db.query(KnowledgeNode.node_name)
        .join(UserWeakPoint, UserWeakPoint.knowledge_node_id == KnowledgeNode.id)
        .filter(UserWeakPoint.user_id == user.id, UserWeakPoint.status == "unmastered")
        .all()
    )
    return [row.node_name for row in rows]


def get_user_weak_node_ids(db: Session, user: User) -> list[str]:
    return list_unmastered_weak_node_names(db, user)


def get_user_knowledge_states(db: Session, user: User) -> dict[str, str]:
    rows = db.query(UserKnowledgeState).filter(UserKnowledgeState.user_id == user.id).all()
    states = {row.node_id: row.status for row in rows}

    for node_name in list_unmastered_weak_node_names(db, user):
        if states.get(node_name) != "mastered":
            states[node_name] = "weak"

    return states


def mark_node_mastered(db: Session, user: User, node_id: str) -> None:
    set_knowledge_state_status(db, user, node_id, "mastered")

    node = db.query(KnowledgeNode).filter(KnowledgeNode.node_name == node_id).first()
    if node:
        weak_point = (
            db.query(UserWeakPoint)
            .filter(
                UserWeakPoint.user_id == user.id,
                UserWeakPoint.knowledge_node_id == node.id,
            )
            .first()
        )
        if weak_point:
            weak_point.status = "mastered"

    db.commit()


def query_weak_points_subgraph(weak_node_ids: list[str]) -> dict:
    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

    nodes = {}
    edges = []
    edge_set = set()

    def add_edge(source, target, relation):
        if not source or not target or not relation:
            return
        edge_id = f"{source}-{relation}-{target}"
        reverse_id = f"{target}-{relation}-{source}"
        if edge_id not in edge_set and reverse_id not in edge_set:
            edge_set.add(edge_id)
            edges.append({
                "id": edge_id,
                "source": source,
                "target": target,
                "relation": relation,
            })

    try:
        with driver.session(database=DB_NAME) as session:
            base_query = """
            MATCH (n)
            WHERE 'Base' IN labels(n)
            RETURN n.name AS name, coalesce(n.desc, '') AS desc, labels(n) AS labels
            """
            base_result = session.run(base_query)
            for record in base_result:
                name = record["name"]
                if name and name not in nodes:
                    nodes[name] = {
                        "id": name,
                        "name": name,
                        "desc": record["desc"] or "",
                        "labels": record["labels"] or [],
                        "is_base": True,
                    }

            if weak_node_ids:
                weak_query = """
                MATCH (n)
                WHERE n.name IN $weak_node_ids
                RETURN n.name AS name, coalesce(n.desc, '') AS desc, labels(n) AS labels
                """
                weak_result = session.run(weak_query, weak_node_ids=weak_node_ids)
                for record in weak_result:
                    name = record["name"]
                    if name and name not in nodes:
                        nodes[name] = {
                            "id": name,
                            "name": name,
                            "desc": record["desc"] or "",
                            "labels": record["labels"] or [],
                            "is_base": False,
                        }

                neighbor_query = """
                MATCH (weak)-[r]-(neighbor)
                WHERE weak.name IN $weak_node_ids AND NOT 'Base' IN labels(neighbor)
                RETURN DISTINCT
                    weak.name AS weak_name,
                    neighbor.name AS neighbor_name,
                    coalesce(neighbor.desc, '') AS neighbor_desc,
                    labels(neighbor) AS neighbor_labels,
                    type(r) AS relation
                """
                neighbor_result = session.run(neighbor_query, weak_node_ids=weak_node_ids)
                for record in neighbor_result:
                    neighbor_name = record["neighbor_name"]
                    if neighbor_name and neighbor_name not in nodes:
                        nodes[neighbor_name] = {
                            "id": neighbor_name,
                            "name": neighbor_name,
                            "desc": record["neighbor_desc"] or "",
                            "labels": record["neighbor_labels"] or [],
                            "is_base": False,
                        }

                    weak_name = record["weak_name"]
                    relation = record["relation"]
                    add_edge(weak_name, neighbor_name, relation)

            all_node_ids = list(nodes.keys())
            if all_node_ids:
                all_edges_query = """
                MATCH (a)-[r]-(b)
                WHERE a.name IN $node_ids AND b.name IN $node_ids
                RETURN DISTINCT a.name AS source, type(r) AS relation, b.name AS target
                """
                all_edges_result = session.run(all_edges_query, node_ids=all_node_ids)
                for record in all_edges_result:
                    source = record["source"]
                    target = record["target"]
                    relation = record["relation"]
                    add_edge(source, target, relation)
    finally:
        driver.close()

    return {"nodes": list(nodes.values()), "edges": edges}


def get_weak_points_graph(db: Session, user: User) -> dict:
    weak_node_ids = get_user_weak_node_ids(db, user)
    graph = query_weak_points_subgraph(weak_node_ids)
    states = get_user_knowledge_states(db, user)

    for node in graph["nodes"]:
        node_id = node["id"]
        status = states.get(node_id, "unknown")
        node["status"] = status

        if status == "weak":
            node["color"] = "#ef4444"
        elif status == "mastered":
            node["color"] = "#22c55e"
        elif status == "learning":
            node["color"] = "#f59e0b"
        else:
            node["color"] = "#94a3b8"

    return graph
