from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_db
from backend.models.user import User
from backend.services.knowledge_state_service import get_weak_points_graph, mark_node_mastered
from backend.services.weak_point_service import list_unmastered_weak_points, mark_weak_point_mastered

router = APIRouter(prefix="/api/weak-points", tags=["weak-points"])


@router.get("")
def get_weak_points(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return list_unmastered_weak_points(db, current_user)


@router.get("/graph")
def get_weak_points_graph_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_weak_points_graph(db, current_user)


@router.post("/{node_id}/mastered", status_code=status.HTTP_204_NO_CONTENT)
def post_mastered(
    node_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mark_weak_point_mastered(db, current_user, node_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/state/{node_id}/mastered", status_code=status.HTTP_204_NO_CONTENT)
def post_state_mastered(
    node_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mark_node_mastered(db, current_user, node_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
