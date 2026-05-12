from __future__ import annotations

from pydantic import AnyHttpUrl
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    environment: str = "local"

    # Supabase
    supabase_url: AnyHttpUrl
    supabase_service_role_key: str

    # JWT
    jwt_access_secret: str
    jwt_refresh_secret: str
    jwt_access_ttl_seconds: int = 60 * 60  # 1 hour
    jwt_refresh_ttl_seconds: int = 7 * 24 * 60 * 60  # 7 days

    # MoMo
    momo_partner_code: str | None = None
    momo_access_key: str | None = None
    momo_secret_key: str | None = None
    momo_endpoint: AnyHttpUrl | None = None  # create payment endpoint

    # Admin (optional): X-Admin-Key header for machine-to-machine admin calls
    admin_api_key: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

