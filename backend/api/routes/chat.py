from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_db
from backend.models.user import User
from backend.schemas.chat import MessageCreateRequest, SessionCreateRequest
from backend.services.chat_service import create_session, list_messages, list_sessions, send_message

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/sessions")
def get_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return list_sessions(db, current_user)


@router.post("/sessions")
def post_session(
    payload: SessionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_session(db, current_user, payload.title)


@router.get("/sessions/{session_id}/messages")
def get_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_messages(db, current_user, session_id)


@router.post("/sessions/{session_id}/messages")
def post_message(
    session_id: int,
    payload: MessageCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return send_message(db, current_user, session_id, payload)
