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
    jwt_access_ttl_seconds: int = 24 * 60 * 60  # 24 hours (CMS admin sessions)
    jwt_refresh_ttl_seconds: int = 7 * 24 * 60 * 60  # 7 days

    # MoMo
    momo_partner_code: str | None = None
    momo_access_key: str | None = None
    momo_secret_key: str | None = None
    momo_endpoint: AnyHttpUrl | None = None  # create payment endpoint

    # Admin (optional): X-Admin-Key header for machine-to-machine admin calls
    admin_api_key: str | None = None

    # Public site URL (GEO: sitemap / llms.txt)
    site_url: str = "https://9well.com"

    # CMS static publish → apps/web/public/v2 (and optional mirrors)
    cms_static_root: str | None = None
    cms_static_mirror: str | None = None  # comma-separated extra roots (e.g. dist/v2)
    cms_seeds_dir: str | None = None
    # Web dist root for GEO fallback files (llms.txt / sitemap.xml / blog/*.md)
    cms_web_dist: str | None = None
    # apps/web root (contains scripts/prerender.mjs) — SEO HTML on blog publish
    cms_web_root: str | None = None
    # When true (or env not local), CMS blog save/publish schedules node prerender
    prerender_on_publish: bool | None = None
    vite_api_base_url: str | None = None
    # Override API base used by node prerender (else localhost or vite_api_base_url)
    prerender_api_base_url: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

