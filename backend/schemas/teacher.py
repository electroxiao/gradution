from datetime import datetime

from pydantic import BaseModel, Field


class TeacherStudentResponse(BaseModel):
    id: int
    username: str
    class_name: str | None = None
    weak_point_count: int
    unfinished_assignment_count: int = 0


class TeacherKnowledgeNodeRefResponse(BaseModel):
    id: int
    node_name: str
    node_type: str | None = None
    chapter: str | None = None
    match_type: str = "match"
    relevance_score: int = 0


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
    chapter: str
    search_match: bool = True
    relevance_score: int = 0


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
    chapter: str | None = Field(default=None, max_length=64)


class GraphNodeUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    desc: str = Field(default="")
    node_type: str | None = Field(default=None, max_length=64)
    chapter: str | None = Field(default=None, max_length=64)


class GraphNodeBatchChapterRequest(BaseModel):
    names: list[str] = Field(default_factory=list)
    chapter: str = Field(min_length=1, max_length=64)


class GraphNodeDescriptionGenerateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class GraphNodeDescriptionGenerateResponse(BaseModel):
    desc: str


class GraphEdgeCreateRequest(BaseModel):
    source: str = Field(min_length=1, max_length=255)
    target: str = Field(min_length=1, max_length=255)
    relation: str = Field(min_length=1, max_length=64)


class GraphEdgeUpdateRequest(BaseModel):
    source: str = Field(min_length=1, max_length=255)
    target: str = Field(min_length=1, max_length=255)
    relation: str = Field(min_length=1, max_length=64)


class DashboardMetricResponse(BaseModel):
    total_students: int
    total_unmastered_weak_points: int
    latest_assignment_title: str | None = None
    latest_assignment_unsubmitted_students: int | None = None
    top_nodes: list[dict]


class TeacherConsultationSummaryResponse(BaseModel):
    knowledge_node_id: int
    node_name: str
    mention_count: int
    student_count: int
    last_seen_at: datetime
