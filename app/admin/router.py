from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from app.admin.content.router import router as content_router
from app.admin.deps import AdminContext, require_admin
from app.admin.models import (
    AdminActivateSubscriptionRequest,
    AdminSubscriptionResponse,
    AdminUserOrder,
    AdminUserResponse,
    AdminUserSubscription,
)
from app.auth.repository import get_user_by_id, list_users
from app.db.supabase_client import get_supabase
from app.membership.subscription_actions import activate_or_extend_subscription
from app.payments.repository import (
    get_package_by_code,
    list_latest_orders_for_users,
    list_subscriptions_for_users,
    mark_latest_pending_order_paid,
)
from app.portal.repository import get_profile, update_profile

router = APIRouter()
router.include_router(content_router)


def _pkg_fields(row: dict | None) -> tuple[str | None, str | None]:
    if not row:
        return None, None
    pkg = row.get("membership_packages")
    if isinstance(pkg, dict):
        return pkg.get("code"), pkg.get("name")
    return None, None


@router.get("/users", response_model=list[AdminUserResponse])
def admin_list_users(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: AdminContext = Depends(require_admin),
    client: Client = Depends(get_supabase),
) -> list[AdminUserResponse]:
    rows = list_users(client, limit=limit, offset=offset)
    ids = [str(r["id"]) for r in rows]
    subs = list_subscriptions_for_users(client, ids)
    orders = list_latest_orders_for_users(client, ids)

    out: list[AdminUserResponse] = []
    for r in rows:
        uid = str(r["id"])
        sub = subs.get(uid)
        order = orders.get(uid)
        sub_model = None
        if sub:
            code, name = _pkg_fields(sub)
            sub_model = AdminUserSubscription(
                status=str(sub.get("status") or "none"),
                package_code=code,
                package_name=name,
                current_period_end=str(sub["current_period_end"]) if sub.get("current_period_end") else None,
            )
        order_model = None
        if order:
            code, name = _pkg_fields(order)
            order_model = AdminUserOrder(
                id=str(order["id"]),
                status=str(order.get("status") or "pending"),
                amount_vnd=int(order.get("amount_vnd") or 0),
                package_code=code,
                package_name=name,
                created_at=str(order.get("created_at") or ""),
            )
        out.append(
            AdminUserResponse(
                id=uid,
                email=r["email"],
                name=r.get("name"),
                role=r.get("role", "user"),
                created_at=str(r["created_at"]),
                subscription=sub_model,
                latest_order=order_model,
            )
        )
    return out


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

    mark_latest_pending_order_paid(client, body.user_id)

    # Keep portal plan_code in sync for hub UX (lesson gate uses subscription only)
    try:
        profile = get_profile(client, body.user_id)
        if profile:
            update_profile(client, body.user_id, {"plan_code": body.package_code})
    except Exception:
        pass

    return AdminSubscriptionResponse(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        package_id=str(row["package_id"]),
        status=str(row["status"]),
        current_period_start=str(row["current_period_start"]),
        current_period_end=str(row["current_period_end"]),
    )
