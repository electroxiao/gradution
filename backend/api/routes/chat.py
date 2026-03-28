from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_db
from backend.models.user import User
from backend.schemas.chat import MessageCreateRequest, SessionCreateRequest, SessionUpdateRequest
from backend.services.chat_service import (
    create_session,
    delete_session,
    list_messages,
    list_sessions,
    rename_session,
    send_message,
    stream_message,
)

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


@router.patch("/sessions/{session_id}")
def patch_session(
    session_id: int,
    payload: SessionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return rename_session(db, current_user, session_id, payload)


@router.delete("/sessions/{session_id}", status_code=204)
def remove_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    delete_session(db, current_user, session_id)


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


@router.post("/sessions/{session_id}/messages/stream")
def post_message_stream(
    session_id: int,
    payload: MessageCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return StreamingResponse(
        stream_message(db, current_user, session_id, payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
