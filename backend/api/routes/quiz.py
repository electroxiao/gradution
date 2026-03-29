import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_db
from backend.models.user import User
from backend.services.quiz_service import (
    generate_quiz_question,
    stream_generate_quiz_question,
    stream_judge_answer,
    submit_and_judge_answer,
)

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


class GenerateQuizRequest(BaseModel):
    node_id: str


class SubmitAnswerRequest(BaseModel):
    node_id: str
    question: str
    answer: str


@router.post("/generate")
def generate_quiz(
    request: GenerateQuizRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quiz = generate_quiz_question(request.node_id)
    return quiz


@router.post("/generate/stream")
def generate_quiz_stream(
    request: GenerateQuizRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    def event_generator():
        for chunk in stream_generate_quiz_question(request.node_id):
            yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/submit")
def submit_answer(
    request: SubmitAnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = submit_and_judge_answer(
        request.node_id,
        request.question,
        request.answer,
        db,
        current_user,
    )
    return result


@router.post("/submit/stream")
def submit_answer_stream(
    request: SubmitAnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    def event_generator():
        for event in stream_judge_answer(
            request.node_id,
            request.question,
            request.answer,
            db,
            current_user,
        ):
            if event["type"] == "feedback_delta":
                yield f"event: feedback_delta\ndata: {json.dumps({'content': event['content']}, ensure_ascii=False)}\n\n"
            elif event["type"] == "result":
                yield f"event: result\ndata: {json.dumps({'is_correct': event['is_correct'], 'mastered': event['mastered']}, ensure_ascii=False)}\n\n"
        yield "event: done\ndata: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
