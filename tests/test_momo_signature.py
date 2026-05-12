from __future__ import annotations

from app.config import get_settings
from app.payments.momo.service import verify_momo_ipn_signature


def test_momo_ipn_signature_invalid_without_secret(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service_role_key")
    monkeypatch.setenv("JWT_ACCESS_SECRET", "access_secret")
    monkeypatch.setenv("JWT_REFRESH_SECRET", "refresh_secret")
    monkeypatch.delenv("MOMO_SECRET_KEY", raising=False)
    get_settings.cache_clear()

    assert verify_momo_ipn_signature({"signature": "x"}) is False

