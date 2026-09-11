"""Fire-and-forget web SEO prerender after CMS blog publish.

Writes apps/web/dist/blog/<slug>/index.html + sitemap via node scripts/prerender.mjs.
Coalesces bursts of saves into one run (queue-after-current).
"""
from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_running = False
_queued = False
_last_started_at: float | None = None
_last_result: dict[str, Any] = {"ok": False, "message": "never-run"}


def _truthy(val: str | None) -> bool:
    return str(val or "").strip().lower() in {"1", "true", "yes", "on"}


def _settings_flag(name: str, default: bool = False) -> bool:
    env = os.environ.get(name)
    if env is not None and str(env).strip() != "":
        return _truthy(env)
    try:
        from app.config import get_settings

        s = get_settings()
        return bool(getattr(s, name.lower(), default))
    except Exception:
        return default


def prerender_enabled() -> bool:
    # Default ON in non-local so VPS works after one env line; local stays opt-in.
    env = os.environ.get("PRERENDER_ON_PUBLISH")
    if env is not None and str(env).strip() != "":
        return _truthy(env)
    try:
        from app.config import get_settings

        s = get_settings()
        explicit = getattr(s, "prerender_on_publish", None)
        if explicit is not None:
            return bool(explicit)
        return str(getattr(s, "environment", "local")).lower() not in {"local", "dev", "test"}
    except Exception:
        return False


def resolve_web_root() -> Path | None:
    for key in ("CMS_WEB_ROOT", "WEB_PRERENDER_CWD"):
        raw = os.environ.get(key, "").strip()
        if raw:
            p = Path(raw)
            if (p / "scripts" / "prerender.mjs").is_file():
                return p

    try:
        from app.config import get_settings

        s = get_settings()
        for attr in ("cms_web_root", "cms_web_dist"):
            raw = getattr(s, attr, None) or ""
            if not raw:
                continue
            p = Path(str(raw).split(",")[0].strip())
            if attr == "cms_web_dist":
                # dist → apps/web
                if p.name == "dist":
                    p = p.parent
            if (p / "scripts" / "prerender.mjs").is_file():
                return p
    except Exception:
        pass

    here = Path(__file__).resolve()
    # .../9wellbackend/app/content/prerender_trigger.py → parents[2]=9wellbackend
    backend_root = here.parents[2]
    candidates = [
        backend_root.parent / "9wellcms" / "apps" / "web",
        Path("/var/www/9wellcms/apps/web"),
        Path.cwd().parent / "9wellcms" / "apps" / "web",
        Path.cwd() / "apps" / "web",
    ]
    for c in candidates:
        if (c / "scripts" / "prerender.mjs").is_file():
            return c
    return None


def _build_env(web_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    api = (
        os.environ.get("VITE_API_BASE_URL")
        or os.environ.get("API_BASE_URL")
        or os.environ.get("PUBLIC_API_BASE_URL")
        or ""
    )
    site = os.environ.get("SITE_URL") or os.environ.get("VITE_SITE_URL") or ""
    try:
        from app.config import get_settings

        s = get_settings()
        if not api:
            api = getattr(s, "vite_api_base_url", None) or ""
        if not site:
            site = getattr(s, "site_url", None) or ""
    except Exception:
        pass
    api = (api or "https://api.9well.com").rstrip("/")
    site = (site or "https://9well.com").rstrip("/")
    env["VITE_API_BASE_URL"] = api
    env["API_BASE_URL"] = api
    env["SITE_URL"] = site
    env["PRERENDER_REQUIRE_API"] = os.environ.get("PRERENDER_REQUIRE_API") or "1"
    env.setdefault("PRERENDER_MIN_POSTS", os.environ.get("PRERENDER_MIN_POSTS") or "50")
    env.setdefault("PRERENDER_CONCURRENCY", os.environ.get("PRERENDER_CONCURRENCY") or "8")
    env["PWD"] = str(web_root)
    return env


def _log_path(web_root: Path) -> Path:
    override = os.environ.get("PRERENDER_LOG", "").strip()
    if override:
        return Path(override)
    log_dir = web_root / "dist"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        log_dir = web_root
    return log_dir / ".prerender.log"


def prerender_status() -> dict[str, Any]:
    with _lock:
        return {
            "enabled": prerender_enabled(),
            "running": _running,
            "queued": _queued,
            "last_started_at": _last_started_at,
            "last_result": dict(_last_result),
            "web_root": str(resolve_web_root() or ""),
        }


def _run_once(reason: str) -> dict[str, Any]:
    global _last_result, _last_started_at
    web_root = resolve_web_root()
    if not web_root:
        result = {"ok": False, "message": "web root with scripts/prerender.mjs not found"}
        _last_result = result
        logger.warning("prerender skip: %s", result["message"])
        return result

    index = web_root / "dist" / "index.html"
    if not index.is_file():
        result = {
            "ok": False,
            "message": f"missing {index} — run vite build once before prerender-on-publish",
        }
        _last_result = result
        logger.warning("prerender skip: %s", result["message"])
        return result

    cmd = ["node", "scripts/prerender.mjs"]
    env = _build_env(web_root)
    log_file = _log_path(web_root)
    _last_started_at = time.time()
    logger.info("prerender start reason=%s cwd=%s", reason, web_root)

    try:
        with open(log_file, "a", encoding="utf-8") as fh:
            fh.write(f"\n--- {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} reason={reason} ---\n")
            fh.flush()
            proc = subprocess.run(
                cmd,
                cwd=str(web_root),
                env=env,
                stdout=fh,
                stderr=subprocess.STDOUT,
                timeout=int(os.environ.get("PRERENDER_TIMEOUT_SEC") or 600),
                check=False,
            )
        if proc.returncode == 0:
            result = {"ok": True, "message": f"prerender ok ({reason})", "log": str(log_file)}
        else:
            result = {
                "ok": False,
                "message": f"prerender exit {proc.returncode} ({reason})",
                "log": str(log_file),
            }
            logger.error("prerender failed: %s", result["message"])
    except subprocess.TimeoutExpired:
        result = {"ok": False, "message": f"prerender timeout ({reason})", "log": str(log_file)}
        logger.error(result["message"])
    except Exception as e:
        result = {"ok": False, "message": f"prerender error: {e}", "log": str(log_file)}
        logger.exception("prerender exception")

    _last_result = result
    return result


def _worker(reason: str) -> None:
    global _running, _queued
    try:
        while True:
            _run_once(reason)
            with _lock:
                if not _queued:
                    _running = False
                    return
                _queued = False
                reason = "queued-rerun"
    except Exception:
        logger.exception("prerender worker crashed")
        with _lock:
            _running = False
            _queued = False


def schedule_web_prerender(reason: str = "cms") -> dict[str, Any]:
    """Schedule background prerender. Safe to call from request handlers."""
    if not prerender_enabled():
        return {"ok": False, "message": "PRERENDER_ON_PUBLISH disabled", "started": False}

    if not resolve_web_root():
        return {
            "ok": False,
            "message": "CMS_WEB_ROOT not set / prerender.mjs not found",
            "started": False,
        }

    global _running, _queued
    with _lock:
        if _running:
            _queued = True
            return {"ok": True, "message": "prerender already running — queued rerun", "started": False, "queued": True}
        _running = True

    threading.Thread(target=_worker, args=(reason,), name="web-prerender", daemon=True).start()
    return {"ok": True, "message": "prerender started", "started": True}
