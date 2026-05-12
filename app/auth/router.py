from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.auth.models import (
    AuthResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    SignupRequest,
    UserResponse,
)
from app.auth.repository import (
    create_user_row,
    get_user_by_email,
    invalidate_refresh_token,
    invalidate_user_refresh_tokens,
    refresh_token_row_exists,
    store_refresh_token,
)
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    verify_password,
    verify_token,
)
from app.config import get_settings
from app.db.supabase_client import get_supabase

router = APIRouter()


@router.post("/signup")
def signup(payload: SignupRequest, client: Client = Depends(get_supabase)) -> dict[str, object]:
    email = str(payload.email).lower()
    if get_user_by_email(client, email):
        raise HTTPException(status_code=409, detail="Email already registered")

    user = create_user_row(
        client,
        email=email,
        name=payload.name,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        provider="email",
        email_verified=False,
    )
    return {"message": "Signup successful", "user": UserResponse.model_validate(user).model_dump()}


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, client: Client = Depends(get_supabase)) -> AuthResponse:
    user = get_user_by_email(client, str(payload.email).lower())
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Password login not available for this user")
    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(user_id=str(user["id"]))
    refresh_token, refresh_exp = create_refresh_token(user_id=str(user["id"]))
    if not store_refresh_token(client, str(user["id"]), refresh_token, refresh_exp.isoformat()):
        raise HTTPException(status_code=500, detail="Failed to persist session")

    return AuthResponse(
        user=UserResponse.model_validate(user),
        token=access_token,
        refreshToken=refresh_token,
    )


@router.post("/refresh")
def refresh(payload: RefreshRequest, client: Client = Depends(get_supabase)) -> dict[str, str]:
    token = payload.refreshToken
    settings = get_settings()
    decoded = verify_token(token, secret=settings.jwt_refresh_secret)
    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user_id = decoded.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    if not refresh_token_row_exists(client, str(user_id), token):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    invalidate_refresh_token(client, token)
    new_access = create_access_token(user_id=str(user_id))
    new_refresh, new_refresh_exp = create_refresh_token(user_id=str(user_id))
    if not store_refresh_token(client, str(user_id), new_refresh, new_refresh_exp.isoformat()):
        raise HTTPException(status_code=500, detail="Failed to persist session")
    return {"token": new_access, "refreshToken": new_refresh}


@router.post("/logout")
def logout(
    payload: LogoutRequest,
    user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase),
) -> dict[str, str]:
    if payload.refreshToken:
        invalidate_refresh_token(client, payload.refreshToken)
    else:
        invalidate_user_refresh_tokens(client, str(user["id"]))
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
def me(user: dict = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user)

