from __future__ import annotations

from app.auth.security import create_access_token, create_refresh_token, verify_token
from app.config import get_settings


def test_access_token_roundtrip(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service_role_key")
    monkeypatch.setenv("JWT_ACCESS_SECRET", "access_secret")
    monkeypatch.setenv("JWT_REFRESH_SECRET", "refresh_secret")
    get_settings.cache_clear()

    tok = create_access_token(user_id="u1")
    payload = verify_token(tok, secret=get_settings().jwt_access_secret)
    assert payload["user_id"] == "u1"
    assert payload["type"] == "access"


def test_refresh_token_roundtrip(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service_role_key")
    monkeypatch.setenv("JWT_ACCESS_SECRET", "access_secret")
    monkeypatch.setenv("JWT_REFRESH_SECRET", "refresh_secret")
    get_settings.cache_clear()

    tok, _exp = create_refresh_token(user_id="u1")
    payload = verify_token(tok, secret=get_settings().jwt_refresh_secret)
    assert payload["user_id"] == "u1"
    assert payload["type"] == "refresh"

