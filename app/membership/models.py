from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class MembershipPackageResponse(BaseModel):
    id: str
    code: str
    name: str
    description: str | None = None
    price_vnd: int
    duration_days: int
    status: str
    sort_order: int


class MyMembershipResponse(BaseModel):
    status: str
    current_period_end: datetime | None = None
    package: MembershipPackageResponse | None = None

