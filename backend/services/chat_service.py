from fastapi import HTTPException, status
from neo4j import GraphDatabase
from openai import OpenAI
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.chat import ChatMessage, ChatSession
from backend.models.user import User
from backend.schemas.chat import ChatTurnResponse, MessageCreateRequest, MessageResponse, SessionResponse
from backend.services import rag_engine
from backend.services.weak_point_service import extract_core_nodes, upsert_weak_points


def list_sessions(db: Session, user: User) -> list[SessionResponse]:
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return [SessionResponse.model_validate(item) for item in sessions]


def create_session(db: Session, user: User, title: str | None = None) -> SessionResponse:
    session = ChatSession(user_id=user.id, title=title or "新对话")
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionResponse.model_validate(session)


def list_messages(db: Session, user: User, session_id: int) -> list[MessageResponse]:
    session = _get_user_session(db, user, session_id)
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .all()
    )
    return [_message_to_schema(message) for message in messages]


def send_message(db: Session, user: User, session_id: int, payload: MessageCreateRequest) -> ChatTurnResponse:
    session = _get_user_session(db, user, session_id)
    user_message = ChatMessage(session_id=session.id, role="user", content=payload.content)
    db.add(user_message)
    db.flush()

    history = _build_history(db, session.id, exclude_message_id=user_message.id)
    driver = GraphDatabase.driver(settings.neo4j_uri, auth=settings.neo4j_auth)
    client = OpenAI(api_key=settings.llm_api_key or None, base_url=settings.llm_base_url)

    try:
        reasoning_trace: list = []
        retrieval_trace: list = []
        keywords = rag_engine.extract_keywords_with_llm(
            client,
            payload.content,
            history=history,
            trace=reasoning_trace,
        )
        facts = rag_engine.query_graph_with_reasoning(
            driver,
            client,
            payload.content,
            keywords=keywords,
            max_depth=payload.rag_depth,
            width=payload.rag_width,
            reasoning_trace=reasoning_trace,
            retrieval_trace=retrieval_trace,
        )
        answer = "".join(rag_engine.ask_deepseek_stream(client, payload.content, facts, history=history))
    finally:
        driver.close()

    user_message.keywords_json = keywords
    user_message.facts_json = facts

    assistant_message = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer,
        keywords_json=keywords,
        facts_json=facts,
        reasoning_trace_json=reasoning_trace,
        retrieval_trace_json=retrieval_trace,
    )
    db.add(assistant_message)

    if session.title == "新对话":
        session.title = payload.content[:10] + "..." if len(payload.content) > 10 else payload.content

    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)

    weak_points_added = upsert_weak_points(db, user, session, extract_core_nodes(facts))
    return ChatTurnResponse(
        user_message=_message_to_schema(user_message),
        assistant_message=_message_to_schema(assistant_message),
        weak_points_added=weak_points_added,
    )


def _get_user_session(db: Session, user: User, session_id: int) -> ChatSession:
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    return session


def _build_history(db: Session, session_id: int, exclude_message_id: int | None = None) -> list[dict]:
    query = db.query(ChatMessage).filter(ChatMessage.session_id == session_id)
    if exclude_message_id is not None:
        query = query.filter(ChatMessage.id != exclude_message_id)
    messages = query.order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc()).all()
    return [
        {
            "role": message.role,
            "content": message.content,
            "keywords": message.keywords_json or [],
        }
        for message in messages
    ]


def _message_to_schema(message: ChatMessage) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        keywords=message.keywords_json or [],
        facts=message.facts_json or [],
        reasoning_trace=message.reasoning_trace_json or [],
        retrieval_trace=message.retrieval_trace_json or [],
        created_at=message.created_at,
    )
