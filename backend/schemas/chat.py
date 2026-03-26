from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    title: str | None = None


class SessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageCreateRequest(BaseModel):
    content: str = Field(min_length=1)
    rag_depth: int = Field(default=2, ge=1, le=4)
    rag_width: int = Field(default=3, ge=1, le=8)


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    keywords: list = []
    facts: list = []
    reasoning_trace: list = []
    retrieval_trace: list = []
    created_at: datetime


class ChatTurnResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
    weak_points_added: list[str]
