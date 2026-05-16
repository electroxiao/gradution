from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_current_teacher, get_db
from backend.models.user import User
from backend.schemas.teacher import (
    GraphEdgeCreateRequest,
    GraphEdgeUpdateRequest,
    GraphNodeBatchChapterRequest,
    GraphNodeDescriptionGenerateRequest,
    GraphNodeCreateRequest,
    GraphNodeUpdateRequest,
    TeacherConsultationSummaryResponse,
)
from backend.services.chat_knowledge_event_service import (
    list_student_consultations,
    list_teacher_consultation_hotspots,
)
from backend.services.teacher_service import (
    create_graph_edge_with_db_sync,
    create_graph_node_with_db_sync,
    delete_graph_edge,
    delete_graph_node,
    generate_graph_node_description,
    get_graph,
    get_weak_point_dashboard,
    list_knowledge_node_refs,
    list_student_weak_points,
    list_students_with_weak_points,
    update_graph_edge,
    update_graph_node,
    update_graph_nodes_chapter,
)

router = APIRouter(prefix="/api/teacher", tags=["teacher"])


def _consultation_summary_response(row) -> TeacherConsultationSummaryResponse:
    return TeacherConsultationSummaryResponse(
        knowledge_node_id=row.node_id,
        node_name=row.node_name,
        mention_count=row.mention_count,
        student_count=row.student_count,
        last_seen_at=row.last_seen_at,
    )


@router.get("/graph")
def get_teacher_graph(
    keyword: str = Query(default="", max_length=255),
    chapter: str = Query(default="", max_length=64),
    limit: int = Query(default=500, ge=1, le=2000),
    current_user: User = Depends(get_current_teacher),
):
    return get_graph(keyword=keyword, chapter=chapter, limit=limit)


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


@router.post("/graph/nodes/batch-chapter")
def post_graph_nodes_batch_chapter(
    payload: GraphNodeBatchChapterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return update_graph_nodes_chapter(db, payload)


@router.patch("/graph/nodes/{node_name:path}")
def patch_graph_node(
    node_name: str,
    payload: GraphNodeUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return update_graph_node(db, node_name, payload)


@router.delete("/graph/nodes/{node_name:path}")
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


@router.get("/consultations/hotspots", response_model=list[TeacherConsultationSummaryResponse])
def get_consultation_hotspots(
    class_name: str | None = None,
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    rows = list_teacher_consultation_hotspots(db, class_name=class_name, limit=limit)
    return [_consultation_summary_response(row) for row in rows]


@router.get("/students/{student_id}/consultations", response_model=list[TeacherConsultationSummaryResponse])
def get_student_consultations(
    student_id: int,
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    rows = list_student_consultations(db, student_id, limit=limit)
    return [_consultation_summary_response(row) for row in rows]


@router.get("/dashboard/weak-points")
def get_teacher_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    return get_weak_point_dashboard(db, current_user)
