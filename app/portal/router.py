from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.auth.models import AuthResponse, UserResponse
from app.auth.repository import create_user_row, get_user_by_email, store_refresh_token
from app.auth.security import create_access_token, create_refresh_token, get_current_user, hash_password
from app.db.supabase_client import get_supabase
from app.portal import models as m
from app.portal.repository import (
    create_checkin,
    create_profile,
    get_profile,
    latest_quiz,
    list_checkins,
    save_quiz_result,
    update_profile,
)
from app.portal.telegram import send_checkin_telegram, send_shop_order_telegram

router = APIRouter(prefix="/portal", tags=["portal"])


def _profile_out(row: dict) -> m.PortalProfileOut:
    privacy = row.get("privacy") or {}
    if not isinstance(privacy, dict):
        privacy = {}
    return m.PortalProfileOut(
        user_id=str(row["user_id"]),
        nickname=row.get("nickname") or "",
        pin_hash=row.get("pin_hash"),
        plan_code=row.get("plan_code") or "none",
        program_started_at=str(row["program_started_at"]) if row.get("program_started_at") else None,
        current_week=int(row.get("current_week") or 1),
        week_done=row.get("week_done") or {},
        privacy=m.PortalPrivacy(**{**m.PortalPrivacy().model_dump(), **privacy}),
        client_code=row.get("client_code") or "",
        trainer_stats=row.get("trainer_stats") or {},
    )


def _checkin_out(row: dict) -> m.PortalCheckinOut:
    return m.PortalCheckinOut(
        id=str(row["id"]),
        week_number=int(row["week_number"]),
        mood=row.get("mood"),
        freq=row.get("freq"),
        control=row.get("control"),
        notes=row.get("notes"),
        created_at=str(row["created_at"]),
    )


@router.post("/register", response_model=AuthResponse)
def portal_register(
    body: m.PortalRegisterRequest,
    client: Client = Depends(get_supabase),
) -> AuthResponse:
    if get_user_by_email(client, str(body.email).lower()):
        raise HTTPException(status_code=409, detail="Email already registered")

    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    email = str(body.email).lower()
    user = create_user_row(
        client,
        email=email,
        name=body.nickname,
        password_hash=hash_password(body.password),
        phone=None,
        provider="email",
        email_verified=False,
    )
    create_profile(client, user_id=user["id"], nickname=body.nickname, pin_hash=body.pin_hash)

    access = create_access_token(user_id=str(user["id"]))
    refresh, refresh_exp = create_refresh_token(user_id=str(user["id"]))
    if not store_refresh_token(client, str(user["id"]), refresh, refresh_exp.isoformat()):
        raise HTTPException(status_code=500, detail="Failed to persist session")

    return AuthResponse(
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user.get("name") or body.nickname,
            phone=user.get("phone"),
            provider=user.get("provider") or "email",
            email_verified=bool(user.get("email_verified")),
            role=user.get("role") or "user",
        ),
        token=access,
        refreshToken=refresh,
    )


@router.get("/me", response_model=m.PortalMeResponse)
def portal_me(
    user: Annotated[dict, Depends(get_current_user)],
    client: Client = Depends(get_supabase),
) -> m.PortalMeResponse:
    row = get_profile(client, user["id"])
    if not row:
        raise HTTPException(status_code=404, detail="Portal profile not found")

    quiz = latest_quiz(client, user["id"])
    return m.PortalMeResponse(
        profile=_profile_out(row),
        checkins=[_checkin_out(c) for c in list_checkins(client, user["id"])],
        latest_quiz=quiz,
    )


@router.patch("/me", response_model=m.PortalProfileOut)
def portal_update_me(
    body: m.PortalProfileUpdate,
    user: Annotated[dict, Depends(get_current_user)],
    client: Client = Depends(get_supabase),
) -> m.PortalProfileOut:
    patch = body.model_dump(exclude_unset=True)
    if "privacy" in patch and patch["privacy"] is not None:
        patch["privacy"] = patch["privacy"] if isinstance(patch["privacy"], dict) else patch["privacy"].model_dump()
    try:
        row = update_profile(client, user["id"], patch)
    except ValueError:
        raise HTTPException(status_code=404, detail="Portal profile not found") from None
    return _profile_out(row)


@router.post("/quiz")
def portal_submit_quiz(
    body: m.PortalQuizSubmit,
    user: Annotated[dict, Depends(get_current_user)],
    client: Client = Depends(get_supabase),
) -> dict:
    row = save_quiz_result(
        client,
        user["id"],
        body.payload(),
    )
    return {"ok": True, "id": str(row["id"])}


@router.post("/checkin", response_model=m.PortalCheckinOut)
def portal_checkin(
    body: m.PortalCheckinCreate,
    user: Annotated[dict, Depends(get_current_user)],
    client: Client = Depends(get_supabase),
) -> m.PortalCheckinOut:
    profile = get_profile(client, user["id"])
    if not profile:
        raise HTTPException(status_code=404, detail="Portal profile not found")

    row = create_checkin(
        client,
        user["id"],
        body.model_dump(),
    )

    send_checkin_telegram(
        nickname=profile.get("nickname") or user.get("name") or "—",
        client_code=profile.get("client_code") or "",
        week_number=body.week_number,
        mood=body.mood,
        freq=body.freq,
        control=body.control,
        notes=body.notes,
    )

    return _checkin_out(row)


@router.post("/shop-order")
def portal_shop_order(body: m.ShopOrderRequest) -> dict:
    ok = send_shop_order_telegram(
        name=body.name,
        phone=body.phone,
        address=body.address,
        note=body.note,
        total=body.total,
        items=[i.model_dump() for i in body.items],
    )
    return {"ok": True, "notified": ok}
