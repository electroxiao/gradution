from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    title: str | None = None


class SessionUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class SessionResponse(BaseModel):
    id: int
    title: str
    message_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageCreateRequest(BaseModel):
    content: str = Field(min_length=1)


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


class ChatConsultationEventResponse(BaseModel):
    id: int
    knowledge_node_id: int
    node_name: str
    session_id: int
    session_title: str
    created_at: datetime


