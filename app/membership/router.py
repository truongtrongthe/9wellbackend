from __future__ import annotations

from fastapi import APIRouter, Depends
from supabase import Client

from app.auth.security import get_current_user
from app.db.supabase_client import get_supabase
from app.membership.models import MembershipPackageResponse, MyMembershipResponse
from app.membership.repository import get_current_subscription_for_user, list_active_packages
router = APIRouter()


@router.get("/packages", response_model=list[MembershipPackageResponse])
def packages(client: Client = Depends(get_supabase)) -> list[MembershipPackageResponse]:
    rows = list_active_packages(client)
    return [MembershipPackageResponse.model_validate(r) for r in rows]


@router.get("/me", response_model=MyMembershipResponse)
def me(
    user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase),
) -> MyMembershipResponse:
    sub = get_current_subscription_for_user(client, str(user["id"]))
    if not sub:
        return MyMembershipResponse(status="none", current_period_end=None, package=None)

    pkg = sub.get("membership_packages")
    return MyMembershipResponse(
        status=str(sub.get("status") or "none"),
        current_period_end=sub.get("current_period_end"),
        package=MembershipPackageResponse.model_validate(pkg) if isinstance(pkg, dict) else None,
    )

