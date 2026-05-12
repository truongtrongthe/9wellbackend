from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ModuleStatus = Literal["locked", "in_progress", "completed"]


class RoadmapModuleItem(BaseModel):
    id: str
    code: str
    title: str
    description: str | None = None
    sequenceOrder: int
    status: ModuleStatus


class RoadmapResponse(BaseModel):
    modules: list[RoadmapModuleItem]


class AiGuidanceResponse(BaseModel):
    message: str | None = None
    source: str | None = None
    createdAt: datetime | None = None


class NoteCreate(BaseModel):
    content: str = Field(min_length=1, max_length=10_000)


class NoteItem(BaseModel):
    id: str
    content: str
    createdAt: datetime
    updatedAt: datetime | None = None


class ProgressPatchBody(BaseModel):
    status: Literal["in_progress", "completed"]
