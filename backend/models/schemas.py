"""Pydantic request / response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Task Schemas ──


class TaskCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=5000)
    project_id: uuid.UUID | None = None


class StepResponse(BaseModel):
    id: uuid.UUID
    order: int
    title: str
    description: str
    status: str
    retry_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CodeArtifactResponse(BaseModel):
    id: uuid.UUID
    file_path: str
    content: str
    language: str | None
    version: int
    created_at: datetime

    model_config = {"from_attributes": True}


class StepDetail(StepResponse):
    """Step with nested code artifacts."""

    code_artifacts: list[CodeArtifactResponse] = []


class TaskResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID | None
    description: str
    status: str
    result_summary: str | None
    total_tokens: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskDetail(TaskResponse):
    steps: list[StepDetail] = []


# ── Pagination ──


class PaginatedTasks(BaseModel):
    items: list[TaskResponse]
    total: int
    page: int
    per_page: int


# ── Project Schemas ──


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    root_path: str = Field(..., min_length=1, max_length=1024)
    description: str | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    root_path: str
    description: str | None
    indexed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Index Schemas ──


class IndexRequest(BaseModel):
    directory: str = Field(..., min_length=1, max_length=2048)
    project_name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class IndexResponse(BaseModel):
    project_id: uuid.UUID
    project_name: str
    files_indexed: int
    message: str


# ── Search Schemas ──


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    project_id: uuid.UUID | None = None
    top_k: int = Field(default=10, ge=1, le=50)


class SearchResultItem(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    code_snippet: str
    chunk_type: str
    name: str
    language: str
    similarity_score: float


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    total: int


# ── WebSocket Schemas ──


class WSMessage(BaseModel):
    """WebSocket message sent to the client during task execution."""

    event: str
    data: dict = {}


# ── Health ──


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    services: dict[str, str] = {}
