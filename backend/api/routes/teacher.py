from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_current_teacher, get_db
from backend.models.user import User
from backend.schemas.teacher import (
    GraphEdgeCreateRequest,
    GraphEdgeUpdateRequest,
    GraphNodeDescriptionGenerateRequest,
    GraphNodeCreateRequest,
    GraphNodeUpdateRequest,
    PendingBatchApproveRequest,
    PendingBatchRejectRequest,
)
from backend.services.teacher_service import (
    approve_pending_graph_batch,
    create_graph_edge_with_db_sync,
    create_graph_node_with_db_sync,
    delete_graph_edge,
    delete_graph_node,
    generate_graph_node_description,
    get_graph,
    get_pending_graph_batch_detail,
    get_weak_point_dashboard,
    list_knowledge_node_refs,
    list_student_mastery,
    list_pending_graph_batches,
    list_student_weak_points,
    reject_pending_graph_batch,
    list_students_with_weak_points,
    update_graph_edge,
    update_graph_node,
)

router = APIRouter(prefix="/api/teacher", tags=["teacher"])


@router.get("/graph")
def get_teacher_graph(
    keyword: str = Query(default="", max_length=255),
    limit: int = Query(default=500, ge=1, le=2000),
    current_user: User = Depends(get_current_teacher),
):
    return get_graph(keyword=keyword, limit=limit)


@router.get("/graph/pending-batches")
def get_pending_graph_batches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return list_pending_graph_batches(db)


@router.get("/graph/pending-batches/{batch_id:path}")
def get_pending_batch_detail(
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return get_pending_graph_batch_detail(db, batch_id)


@router.post("/graph/pending-batches/{batch_id:path}/approve")
def approve_pending_batch(
    batch_id: str,
    payload: PendingBatchApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return approve_pending_graph_batch(db, current_user, batch_id, payload)


@router.post("/graph/pending-batches/{batch_id:path}/reject")
def reject_pending_batch(
    batch_id: str,
    payload: PendingBatchRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return reject_pending_graph_batch(db, current_user, batch_id, payload)


@router.post("/graph/nodes")
def post_graph_node(
    payload: GraphNodeCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return create_graph_node_with_db_sync(db, payload)


@router.post("/graph/nodes/generate-description")
def post_graph_node_description(
    payload: GraphNodeDescriptionGenerateRequest,
    current_user: User = Depends(get_current_teacher),
):
    return generate_graph_node_description(payload.name)


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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return create_graph_edge_with_db_sync(db, payload)


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


@router.get("/knowledge-nodes")
def get_knowledge_nodes(
    keyword: str = Query(default="", max_length=255),
    include_neighbors: bool = Query(default=False),
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return list_knowledge_node_refs(
        db,
        keyword=keyword,
        include_neighbors=include_neighbors,
        limit=limit,
    )


@router.get("/students/{student_id}/weak-points")
def get_student_weak_points(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return list_student_weak_points(db, student_id)


@router.get("/students/{student_id}/mastery")
def get_student_mastery(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return list_student_mastery(db, student_id)


@router.get("/students/{student_id}/portrait")
def get_student_portrait(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    from backend.services.portrait_service import generate_student_portrait
    return generate_student_portrait(db, student_id)


@router.get("/students/{student_id}/portrait/summary")
def get_student_portrait_summary(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    from backend.services.portrait_service import generate_student_portrait_summary
    return generate_student_portrait_summary(db, student_id)


@router.get("/dashboard/weak-points")
def get_teacher_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return get_weak_point_dashboard(db)
