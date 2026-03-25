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
    steps: list[StepResponse] = []


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


# ── Health ──


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    services: dict[str, str] = {}
