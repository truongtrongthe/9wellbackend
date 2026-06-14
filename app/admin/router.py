from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from app.admin.content.router import router as content_router
from app.admin.deps import AdminContext, require_admin
from app.admin.models import (
    AdminActivateSubscriptionRequest,
    AdminSubscriptionResponse,
    AdminUserResponse,
)
from app.auth.repository import get_user_by_id, list_users
from app.db.supabase_client import get_supabase
from app.membership.subscription_actions import activate_or_extend_subscription
from app.payments.repository import get_package_by_code

router = APIRouter()
router.include_router(content_router)


@router.get("/users", response_model=list[AdminUserResponse])
def admin_list_users(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: AdminContext = Depends(require_admin),
    client: Client = Depends(get_supabase),
) -> list[AdminUserResponse]:
    rows = list_users(client, limit=limit, offset=offset)
    return [
        AdminUserResponse(
            id=str(r["id"]),
            email=r["email"],
            name=r.get("name"),
            role=r.get("role", "user"),
            created_at=str(r["created_at"]),
        )
        for r in rows
    ]


@router.post("/subscriptions/activate", response_model=AdminSubscriptionResponse)
def admin_activate_subscription(
    body: AdminActivateSubscriptionRequest,
    _admin: AdminContext = Depends(require_admin),
    client: Client = Depends(get_supabase),
) -> AdminSubscriptionResponse:
    target = get_user_by_id(client, body.user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    pkg = get_package_by_code(client, body.package_code)
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")

    duration = body.duration_days if body.duration_days is not None else int(pkg["duration_days"])
    if duration <= 0:
        raise HTTPException(status_code=400, detail="durationDays must be positive when set")

    try:
        row = activate_or_extend_subscription(
            client,
            user_id=body.user_id,
            package_id=str(pkg["id"]),
            duration_days=duration,
            status=body.status,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return AdminSubscriptionResponse(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        package_id=str(row["package_id"]),
        status=str(row["status"]),
        current_period_start=str(row["current_period_start"]),
        current_period_end=str(row["current_period_end"]),
    )
