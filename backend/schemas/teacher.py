from datetime import datetime

from pydantic import BaseModel, Field


class TeacherStudentResponse(BaseModel):
    id: int
    username: str
    weak_point_count: int


class TeacherStudentWeakPointResponse(BaseModel):
    id: int
    node_name: str
    status: str
    first_seen_at: datetime
    last_seen_at: datetime


class GraphNodeResponse(BaseModel):
    id: str
    label: str
    name: str
    desc: str
    node_type: str


class GraphEdgeResponse(BaseModel):
    id: str
    edge_key: str
    source: str
    target: str
    source_name: str
    target_name: str
    label: str
    relation: str


class GraphQueryResponse(BaseModel):
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]


class GraphNodeCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    desc: str = Field(default="")
    node_type: str | None = Field(default=None, max_length=64)


class GraphNodeUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    desc: str = Field(default="")
    node_type: str | None = Field(default=None, max_length=64)


class GraphEdgeCreateRequest(BaseModel):
    source: str = Field(min_length=1, max_length=255)
    target: str = Field(min_length=1, max_length=255)
    relation: str = Field(min_length=1, max_length=64)


class GraphEdgeUpdateRequest(BaseModel):
    source: str = Field(min_length=1, max_length=255)
    target: str = Field(min_length=1, max_length=255)
    relation: str = Field(min_length=1, max_length=64)


class PendingNodeProposalEdgeResponse(BaseModel):
    id: int
    source: str
    target: str
    relation: str
    direction: str


class PendingNodeProposalResponse(BaseModel):
    id: int
    name: str
    desc: str
    node_type: str
    reason: str
    status: str
    source_weak_point: str | None = None
    source_user_id: int | None = None
    source_chat_session_id: int | None = None
    created_at: datetime
    suggested_edges: list[PendingNodeProposalEdgeResponse]


class PendingNodeProposalEdgeInput(BaseModel):
    source: str = Field(min_length=1, max_length=255)
    target: str = Field(min_length=1, max_length=255)
    relation: str = Field(default="DEPENDS_ON", min_length=1, max_length=64)
    direction: str = Field(default="out", max_length=16)


class PendingNodeApproveRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    desc: str = Field(default="")
    node_type: str | None = Field(default=None, max_length=64)
    suggested_edges: list[PendingNodeProposalEdgeInput] = Field(default_factory=list)


class PendingNodeRejectRequest(BaseModel):
    note: str = Field(default="", max_length=1000)


class DashboardMetricResponse(BaseModel):
    total_students: int
    total_unmastered_weak_points: int
    affected_students: int
    top_nodes: list[dict]
