from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_current_teacher, get_db
from backend.models.user import User
from backend.schemas.teacher import (
    GraphEdgeCreateRequest,
    GraphEdgeUpdateRequest,
    GraphNodeCreateRequest,
    GraphNodeUpdateRequest,
)
from backend.services.teacher_service import (
    create_graph_edge,
    create_graph_node,
    delete_graph_edge,
    delete_graph_node,
    get_graph,
    get_weak_point_dashboard,
    list_student_weak_points,
    list_students_with_weak_points,
    update_graph_edge,
    update_graph_node,
)

router = APIRouter(prefix="/api/teacher", tags=["teacher"])


@router.get("/graph")
def get_teacher_graph(
    keyword: str = Query(default="", max_length=255),
    limit: int = Query(default=80, ge=1, le=200),
    current_user: User = Depends(get_current_teacher),
):
    return get_graph(keyword=keyword, limit=limit)


@router.post("/graph/nodes")
def post_graph_node(
    payload: GraphNodeCreateRequest,
    current_user: User = Depends(get_current_teacher),
):
    return create_graph_node(payload)


@router.patch("/graph/nodes/{node_name}")
def patch_graph_node(
    node_name: str,
    payload: GraphNodeUpdateRequest,
    current_user: User = Depends(get_current_teacher),
):
    return update_graph_node(node_name, payload)


@router.delete("/graph/nodes/{node_name}")
def remove_graph_node(
    node_name: str,
    current_user: User = Depends(get_current_teacher),
):
    return delete_graph_node(node_name)


@router.post("/graph/edges")
def post_graph_edge(
    payload: GraphEdgeCreateRequest,
    current_user: User = Depends(get_current_teacher),
):
    return create_graph_edge(payload)


@router.patch("/graph/edges/{edge_id:path}")
def patch_graph_edge(
    edge_id: str,
    payload: GraphEdgeUpdateRequest,
    current_user: User = Depends(get_current_teacher),
):
    return update_graph_edge(edge_id, payload)


@router.delete("/graph/edges/{edge_id:path}")
def remove_graph_edge(
    edge_id: str,
    current_user: User = Depends(get_current_teacher),
):
    return delete_graph_edge(edge_id)


@router.get("/students")
def get_students(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return list_students_with_weak_points(db)


@router.get("/students/{student_id}/weak-points")
def get_student_weak_points(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return list_student_weak_points(db, student_id)


@router.get("/dashboard/weak-points")
def get_teacher_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return get_weak_point_dashboard(db)
