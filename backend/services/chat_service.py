import json
import logging
from functools import lru_cache
from threading import Thread
from time import perf_counter

from fastapi import HTTPException, status
from openai import OpenAI
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.db.session import SessionLocal
from backend.models.chat import ChatMessage, ChatSession
from backend.models.user import User
from backend.schemas.chat import (
    MessageCreateRequest,
    MessageResponse,
    SessionResponse,
    SessionUpdateRequest,
)
from backend.services.chat_knowledge_event_service import record_turn_knowledge_events
from backend.services.neo4j_service import close_neo4j_driver

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    return OpenAI(api_key=settings.llm_api_key or None, base_url=settings.llm_base_url)


def close_cached_clients() -> None:
    openai_client = get_openai_client()
    close_method = getattr(openai_client, "close", None)
    if callable(close_method):
        close_method()

    close_neo4j_driver()

    get_openai_client.cache_clear()


def list_sessions(db: Session, user: User) -> list[SessionResponse]:
    message_counts = (
        db.query(ChatMessage.session_id, func.count(ChatMessage.id).label("message_count"))
        .group_by(ChatMessage.session_id)
        .subquery()
    )
    rows = (
        db.query(ChatSession, func.coalesce(message_counts.c.message_count, 0).label("message_count"))
        .outerjoin(message_counts, message_counts.c.session_id == ChatSession.id)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return [
        SessionResponse(
            id=session.id,
            title=session.title,
            message_count=message_count,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
        for session, message_count in rows
    ]


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
    return trimmed[:10]


def _generate_session_title(client: OpenAI, user_input: str, assistant_output: str) -> str:
    prompt = f"""
你是对话标题生成助手。请根据一轮问答生成一个简洁的中文会话标题。

要求：
1. 只输出标题，不要解释。
2. 标题控制在 10 个中文字符以内。
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
        return title[:10] if title else _fallback_session_title(user_input)
    except Exception as error:
        print(f"[chat_title] 自动生成标题失败: {error}")
        return _fallback_session_title(user_input)


def _stream_direct_tutor_answer(client: OpenAI, user_input: str, history: list[dict]):
    system_prompt = """你是一个面向学生的 Java 编程作业辅导老师。
请直接回答学生当前问题，优先帮助学生理解概念、定位错误和形成调试思路。
要求：
1. 使用中文，语气耐心、清晰。
2. 不要编造项目知识图谱中没有提供的事实。
3. 可以给出简短 Java 示例，但不要替学生完成整份作业。
4. 先回答核心原因，再给出可执行的检查步骤。"""
    messages = [{"role": "system", "content": system_prompt}]
    for item in history[-6:]:
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_input})

    stream = client.chat.completions.create(
        model=settings.llm_model_name,
        messages=messages,
        temperature=0.2,
        stream=True,
    )
    for chunk in stream:
        choices = getattr(chunk, "choices", None) or []
        if not choices:
            continue
        delta = getattr(choices[0], "delta", None)
        content = getattr(delta, "content", None)
        if content:
            yield content


def stream_message(db: Session, user: User, session_id: int, payload: MessageCreateRequest):
    request_started_at = perf_counter()
    session = _get_user_session(db, user, session_id)
    user_message = ChatMessage(session_id=session.id, role="user", content=payload.content)
    db.add(user_message)
    db.flush()

    history = _build_history(db, session.id, exclude_message_id=user_message.id)
    client = get_openai_client()
    should_autogenerate_title = _should_autogenerate_title(session, history)

    yield _sse_event("user_message", _message_to_schema(user_message).model_dump(mode="json"))

    answer_started_at = perf_counter()
    chunks: list[str] = []
    try:
        for chunk in _stream_direct_tutor_answer(client, payload.content, history):
            chunks.append(chunk)
            yield _sse_event("assistant_delta", {"content": chunk})
        answer = "".join(chunks)
        answer_elapsed = perf_counter() - answer_started_at
    except Exception:
        db.rollback()
        logger.exception("聊天回答生成失败: session=%s user=%s", session_id, user.id)
        yield _sse_event("error", {"message": "回答生成失败，请稍后重试。"})
        return

    assistant_message = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer,
    )
    db.add(assistant_message)

    if should_autogenerate_title:
        session.title = _generate_session_title(client, payload.content, answer)

    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)

    assistant_schema = _message_to_schema(assistant_message)

    print(
        "[chat_timing] "
        f"session={session.id} "
        f"answer={answer_elapsed:.2f}s "
        f"total={perf_counter() - request_started_at:.2f}s"
    )

    _schedule_turn_knowledge_extraction(
        user_id=user.id,
        session_id=session.id,
        user_message_id=user_message.id,
        assistant_message_id=assistant_message.id,
        previous_context=history[-2:],
    )
    yield _sse_event(
        "assistant_done",
        {
            "assistant_message": assistant_schema.model_dump(mode="json"),
            "weak_points_added": [],
        },
    )


def _schedule_turn_knowledge_extraction(
    *,
    user_id: int,
    session_id: int,
    user_message_id: int,
    assistant_message_id: int,
    previous_context: list[dict] | None = None,
) -> None:
    thread = Thread(
        target=_run_turn_knowledge_extraction,
        kwargs={
            "user_id": user_id,
            "session_id": session_id,
            "user_message_id": user_message_id,
            "assistant_message_id": assistant_message_id,
            "previous_context": previous_context,
        },
        daemon=True,
    )
    thread.start()


def _run_turn_knowledge_extraction(
    *,
    user_id: int,
    session_id: int,
    user_message_id: int,
    assistant_message_id: int,
    previous_context: list[dict] | None = None,
) -> None:
    task_db = SessionLocal()
    try:
        user = task_db.get(User, user_id)
        session = task_db.get(ChatSession, session_id)
        user_message = task_db.get(ChatMessage, user_message_id)
        assistant_message = task_db.get(ChatMessage, assistant_message_id)
        if not all([user, session, user_message, assistant_message]):
            logger.warning(
                "跳过聊天知识点抽取，记录不存在: user=%s session=%s user_message=%s assistant_message=%s",
                user_id,
                session_id,
                user_message_id,
                assistant_message_id,
            )
            return

        context_text = None
        if previous_context:
            context_text = json.dumps(previous_context, ensure_ascii=False)
        inserted_nodes = record_turn_knowledge_events(
            task_db,
            get_openai_client(),
            user,
            session,
            user_message,
            assistant_message,
            previous_context=context_text,
        )
        task_db.commit()
        logger.info(
            "聊天知识点抽取完成: session=%s user_message=%s assistant_message=%s nodes=%s",
            session_id,
            user_message_id,
            assistant_message_id,
            inserted_nodes,
        )
    except Exception:
        task_db.rollback()
        logger.exception(
            "聊天知识点抽取失败: session=%s user_message=%s assistant_message=%s",
            session_id,
            user_message_id,
            assistant_message_id,
        )
    finally:
        task_db.close()


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
        }
        for message in messages
    ]


def _message_to_schema(message: ChatMessage) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
    )


def _sse_event(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
