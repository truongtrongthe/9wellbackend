from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AdminActivateSubscriptionRequest(BaseModel):
    user_id: str = Field(alias="userId")
    package_code: str = Field(alias="packageCode")
    duration_days: int | None = Field(default=None, alias="durationDays")
    status: Literal["active", "trial"] = "active"

    model_config = {"populate_by_name": True}


class AdminUserResponse(BaseModel):
    id: str
    email: str
    name: str | None = None
    role: str
    created_at: str


class AdminSubscriptionResponse(BaseModel):
    id: str
    user_id: str
    package_id: str
    status: str
    current_period_start: str
    current_period_end: str
