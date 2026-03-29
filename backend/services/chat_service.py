import json
from functools import lru_cache
from time import perf_counter

from fastapi import HTTPException, status
from neo4j import GraphDatabase
from openai import OpenAI
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.chat import ChatMessage, ChatSession
from backend.models.user import User
from backend.schemas.chat import (
    ChatTurnResponse,
    MessageCreateRequest,
    MessageResponse,
    SessionResponse,
    SessionUpdateRequest,
)
from backend.services import rag_engine
from backend.services.weak_point_service import extract_core_nodes, upsert_weak_points


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    return OpenAI(api_key=settings.llm_api_key or None, base_url=settings.llm_base_url)


@lru_cache(maxsize=1)
def get_neo4j_driver():
    return GraphDatabase.driver(settings.neo4j_uri, auth=settings.neo4j_auth)


def close_cached_clients() -> None:
    openai_client = get_openai_client()
    close_method = getattr(openai_client, "close", None)
    if callable(close_method):
        close_method()

    driver = get_neo4j_driver()
    driver.close()

    get_openai_client.cache_clear()
    get_neo4j_driver.cache_clear()


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


def rename_session(db: Session, user: User, session_id: int, payload: SessionUpdateRequest) -> SessionResponse:
    session = _get_user_session(db, user, session_id)
    session.title = payload.title.strip()
    db.commit()
    db.refresh(session)
    return SessionResponse.model_validate(session)


def delete_session(db: Session, user: User, session_id: int) -> None:
    session = _get_user_session(db, user, session_id)
    db.delete(session)
    db.commit()


def list_messages(db: Session, user: User, session_id: int) -> list[MessageResponse]:
    session = _get_user_session(db, user, session_id)
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .all()
    )
    return [_message_to_schema(message) for message in messages]


def _should_autogenerate_title(session: ChatSession, history: list[dict]) -> bool:
    return session.title == "新对话" and len(history) == 0


def _fallback_session_title(user_input: str) -> str:
    trimmed = " ".join((user_input or "").split())
    if not trimmed:
        return "新对话"
    return trimmed[:18] + "..." if len(trimmed) > 18 else trimmed


def _generate_session_title(client: OpenAI, user_input: str, assistant_output: str) -> str:
    prompt = f"""
你是对话标题生成助手。请根据一轮问答生成一个简洁的中文会话标题。

要求：
1. 只输出标题，不要解释。
2. 标题控制在 8 到 18 个中文字符以内。
3. 尽量概括知识点或问题核心，不要使用“关于”“请问”等空泛表达。
4. 不要加引号、书名号、句号。

用户问题：
{user_input}

助手回答：
{assistant_output}
"""
    try:
        started_at = perf_counter()
        response = client.chat.completions.create(
            model=settings.llm_model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        title = (response.choices[0].message.content or "").strip()
        title = title.replace("\n", " ").strip("“”\"'。；;：:，, ")
        print(f"[chat_timing] title={perf_counter() - started_at:.2f}s")
        return title[:30] if title else _fallback_session_title(user_input)
    except Exception as error:
        print(f"[chat_title] 自动生成标题失败: {error}")
        return _fallback_session_title(user_input)


def send_message(db: Session, user: User, session_id: int, payload: MessageCreateRequest) -> ChatTurnResponse:
    request_started_at = perf_counter()
    session = _get_user_session(db, user, session_id)
    user_message = ChatMessage(session_id=session.id, role="user", content=payload.content)
    db.add(user_message)
    db.flush()

    history = _build_history(db, session.id, exclude_message_id=user_message.id)
    driver = get_neo4j_driver()
    client = get_openai_client()
    should_autogenerate_title = _should_autogenerate_title(session, history)

    reasoning_trace: list = []
    retrieval_trace: list = []

    keyword_started_at = perf_counter()
    keywords = rag_engine.extract_keywords_with_llm(
        client,
        payload.content,
        history=history,
        trace=reasoning_trace,
    )
    keyword_elapsed = perf_counter() - keyword_started_at

    graph_started_at = perf_counter()
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
    graph_elapsed = perf_counter() - graph_started_at

    answer_started_at = perf_counter()
    answer = "".join(rag_engine.ask_deepseek_stream(client, payload.content, facts, history=history))
    answer_elapsed = perf_counter() - answer_started_at

    print(
        "[chat_timing] "
        f"session={session.id} "
        f"keyword={keyword_elapsed:.2f}s "
        f"graph={graph_elapsed:.2f}s "
        f"answer={answer_elapsed:.2f}s "
        f"total={perf_counter() - request_started_at:.2f}s"
    )

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

    if should_autogenerate_title:
        session.title = _generate_session_title(client, payload.content, answer)

    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)

    weak_points_added = upsert_weak_points(db, user, session, extract_core_nodes(facts))
    return ChatTurnResponse(
        user_message=_message_to_schema(user_message),
        assistant_message=_message_to_schema(assistant_message),
        weak_points_added=weak_points_added,
    )


def stream_message(db: Session, user: User, session_id: int, payload: MessageCreateRequest):
    request_started_at = perf_counter()
    session = _get_user_session(db, user, session_id)
    user_message = ChatMessage(session_id=session.id, role="user", content=payload.content)
    db.add(user_message)
    db.flush()

    history = _build_history(db, session.id, exclude_message_id=user_message.id)
    driver = get_neo4j_driver()
    client = get_openai_client()
    should_autogenerate_title = _should_autogenerate_title(session, history)

    reasoning_trace: list = []
    retrieval_trace: list = []

    keyword_started_at = perf_counter()
    keywords = rag_engine.extract_keywords_with_llm(
        client,
        payload.content,
        history=history,
        trace=reasoning_trace,
    )
    keyword_elapsed = perf_counter() - keyword_started_at

    graph_started_at = perf_counter()
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
    graph_elapsed = perf_counter() - graph_started_at

    user_message.keywords_json = keywords
    user_message.facts_json = facts
    db.flush()

    yield _sse_event("user_message", _message_to_schema(user_message).model_dump(mode="json"))

    answer_started_at = perf_counter()
    chunks: list[str] = []
    for chunk in rag_engine.ask_deepseek_stream(client, payload.content, facts, history=history):
        chunks.append(chunk)
        yield _sse_event("assistant_delta", {"content": chunk})
    answer = "".join(chunks)
    answer_elapsed = perf_counter() - answer_started_at

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

    if should_autogenerate_title:
        session.title = _generate_session_title(client, payload.content, answer)

    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)

    weak_points_added = upsert_weak_points(db, user, session, extract_core_nodes(facts))
    assistant_schema = _message_to_schema(assistant_message)

    print(
        "[chat_timing] "
        f"session={session.id} "
        f"keyword={keyword_elapsed:.2f}s "
        f"graph={graph_elapsed:.2f}s "
        f"answer={answer_elapsed:.2f}s "
        f"total={perf_counter() - request_started_at:.2f}s"
    )

    yield _sse_event(
        "assistant_done",
        {
            "assistant_message": assistant_schema.model_dump(mode="json"),
            "weak_points_added": weak_points_added,
        },
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


def _sse_event(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
