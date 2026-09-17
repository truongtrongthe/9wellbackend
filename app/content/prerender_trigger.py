"""Fire-and-forget web SEO prerender after CMS blog publish.

Writes apps/web/dist/blog/<slug>/index.html + sitemap via node scripts/prerender.mjs.
Coalesces bursts of saves into one run (queue-after-current).
Supports incremental PRERENDER_TOUCH_SLUGS for fast post-publish updates.

Status is persisted to dist/.prerender-status.json so every API worker sees the same result.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_running = False
_queued = False
_queued_slugs: set[str] = set()
_last_started_at: float | None = None
_last_result: dict[str, Any] = {"ok": False, "message": "never-run"}


def _truthy(val: str | None) -> bool:
    return str(val or "").strip().lower() in {"1", "true", "yes", "on"}


def prerender_enabled() -> bool:
    """Default ON when CMS_WEB_ROOT is set, or env not local; explicit flag wins."""
    env = os.environ.get("PRERENDER_ON_PUBLISH")
    if env is not None and str(env).strip() != "":
        return _truthy(env)
    if os.environ.get("CMS_WEB_ROOT", "").strip():
        return True
    try:
        from app.config import get_settings

        s = get_settings()
        explicit = getattr(s, "prerender_on_publish", None)
        if explicit is not None:
            return bool(explicit)
        if getattr(s, "cms_web_root", None):
            return True
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
            if attr == "cms_web_dist" and p.name == "dist":
                p = p.parent
            if (p / "scripts" / "prerender.mjs").is_file():
                return p
    except Exception:
        pass

    here = Path(__file__).resolve()
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


def _status_path(web_root: Path | None = None) -> Path | None:
    override = os.environ.get("PRERENDER_STATUS_FILE", "").strip()
    if override:
        return Path(override)
    root = web_root or resolve_web_root()
    if not root:
        return None
    dist = root / "dist"
    try:
        dist.mkdir(parents=True, exist_ok=True)
    except OSError:
        return root / ".prerender-status.json"
    return dist / ".prerender-status.json"


def _write_status(payload: dict[str, Any], web_root: Path | None = None) -> None:
    path = _status_path(web_root)
    if not path:
        return
    data = {
        **payload,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "web_root": str(web_root or resolve_web_root() or ""),
    }
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as e:
        logger.warning("prerender status write failed: %s", e)


def _read_status_file() -> dict[str, Any]:
    path = _status_path()
    if not path or not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _slug_from_reason(reason: str) -> str | None:
    if ":" not in reason:
        return None
    slug = reason.split(":", 1)[1].strip()
    if not slug or "/" in slug or " " in slug:
        return None
    if slug.startswith("blog-"):
        return None
    return slug


def _resolve_api_base() -> str:
    """Prefer PRERENDER_API_BASE_URL, else localhost on VPS, else public API."""
    dedicated = (os.environ.get("PRERENDER_API_BASE_URL") or "").strip()
    if dedicated:
        return dedicated.rstrip("/")

    local = (os.environ.get("PRERENDER_LOCAL_API") or "http://127.0.0.1:6789").rstrip("/")
    prefer_flag = os.environ.get("PRERENDER_PREFER_LOCAL_API")
    if prefer_flag is None or str(prefer_flag).strip() == "":
        # Default: same-host when CMS_WEB_ROOT points at the VPS web tree
        root = resolve_web_root()
        prefer_local = bool(root and str(root).startswith("/var/www"))
    else:
        prefer_local = _truthy(prefer_flag)
    if prefer_local:
        return local

    explicit = (
        os.environ.get("VITE_API_BASE_URL")
        or os.environ.get("API_BASE_URL")
        or os.environ.get("PUBLIC_API_BASE_URL")
        or ""
    ).strip()
    try:
        from app.config import get_settings

        s = get_settings()
        if not explicit:
            explicit = (
                getattr(s, "prerender_api_base_url", None) or getattr(s, "vite_api_base_url", None) or ""
            ) or ""
    except Exception:
        pass
    return (explicit or "https://api.9well.com").rstrip("/")


def _build_env(web_root: Path, touch_slugs: list[str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    api = _resolve_api_base()
    site = os.environ.get("SITE_URL") or os.environ.get("VITE_SITE_URL") or ""
    try:
        from app.config import get_settings

        s = get_settings()
        if not site:
            site = getattr(s, "site_url", None) or ""
    except Exception:
        pass
    site = (site or "https://9well.com").rstrip("/")
    env["VITE_API_BASE_URL"] = api
    env["API_BASE_URL"] = api
    env["SITE_URL"] = site
    env["PRERENDER_REQUIRE_API"] = os.environ.get("PRERENDER_REQUIRE_API") or "1"
    env.setdefault("PRERENDER_MIN_POSTS", os.environ.get("PRERENDER_MIN_POSTS") or "50")
    env.setdefault("PRERENDER_CONCURRENCY", os.environ.get("PRERENDER_CONCURRENCY") or "8")
    if touch_slugs:
        env["PRERENDER_TOUCH_SLUGS"] = ",".join(sorted(set(touch_slugs)))
        env.pop("PRERENDER_FULL", None)
    else:
        env["PRERENDER_FULL"] = "1"
        env.pop("PRERENDER_TOUCH_SLUGS", None)
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


def _node_bin() -> str:
    return os.environ.get("NODE_BIN") or shutil.which("node") or "node"


def remove_prerendered_slug(slug: str) -> dict[str, Any]:
    """Delete dist/blog/<slug> HTML + .md immediately (unpublish / delete)."""
    web_root = resolve_web_root()
    if not web_root or not slug or "/" in slug:
        return {"ok": False, "message": "cannot remove slug (no web root or bad slug)"}
    blog = web_root / "dist" / "blog"
    removed: list[str] = []
    for path in (blog / slug, blog / f"{slug}.md", blog / slug / "index.html"):
        try:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
                removed.append(str(path))
            elif path.is_file():
                path.unlink(missing_ok=True)
                removed.append(str(path))
        except OSError as e:
            logger.warning("remove prerender %s: %s", path, e)
    # Also remove directory if left empty after index.html delete
    slug_dir = blog / slug
    if slug_dir.is_dir():
        shutil.rmtree(slug_dir, ignore_errors=True)
        removed.append(str(slug_dir))
    return {"ok": True, "message": f"removed {len(removed)} path(s) for {slug}", "removed": removed}


def _verify_touch_slugs(web_root: Path, touch_slugs: list[str], site_url: str) -> dict[str, Any]:
    """Ensure each touch slug has HTML with the correct canonical."""
    failures: list[str] = []
    for slug in touch_slugs:
        html_path = web_root / "dist" / "blog" / slug / "index.html"
        if not html_path.is_file():
            failures.append(f"{slug}: missing index.html")
            continue
        try:
            html = html_path.read_text(encoding="utf-8", errors="ignore")
        except OSError as e:
            failures.append(f"{slug}: read error {e}")
            continue
        expected = f"{site_url.rstrip('/')}/blog/{slug}"
        m = re.search(
            r'rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']|href=["\']([^"\']+)["\'][^>]*rel=["\']canonical["\']',
            html,
            re.I,
        )
        canon = (m.group(1) or m.group(2)) if m else None
        if not canon or expected not in canon:
            failures.append(f"{slug}: canonical={canon!r} expected={expected!r}")
    if failures:
        return {"ok": False, "message": "; ".join(failures)}
    return {"ok": True, "message": f"verified {len(touch_slugs)} slug(s)"}


def prerender_status() -> dict[str, Any]:
    file_status = _read_status_file()
    with _lock:
        mem = {
            "enabled": prerender_enabled(),
            "running": _running,
            "queued": _queued,
            "queued_slugs": sorted(_queued_slugs),
            "last_started_at": _last_started_at,
            "last_result": dict(_last_result),
            "web_root": str(resolve_web_root() or ""),
            "status_file": str(_status_path() or ""),
        }
    # Prefer file for cross-worker last_result / finished state
    if file_status:
        mem["last_result"] = {
            "ok": file_status.get("ok"),
            "message": file_status.get("message"),
            "log": file_status.get("log"),
            "exit_code": file_status.get("exit_code"),
            "mode": file_status.get("mode"),
            "touch_slugs": file_status.get("touch_slugs"),
            "finished_at": file_status.get("finished_at"),
            "started_at": file_status.get("started_at"),
            "verify": file_status.get("verify"),
        }
        if file_status.get("running") is True and not _running:
            # Another worker may still be running
            mem["running"] = True
        if file_status.get("started_at") and not mem["last_started_at"]:
            mem["last_started_at"] = file_status.get("started_at")
        mem["file"] = file_status
    return mem


def _run_once(reason: str, touch_slugs: list[str] | None = None) -> dict[str, Any]:
    global _last_result, _last_started_at
    web_root = resolve_web_root()
    started_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    mode = f"touch={','.join(touch_slugs)}" if touch_slugs else "full"

    if not web_root:
        result = {
            "ok": False,
            "message": "web root with scripts/prerender.mjs not found",
            "started_at": started_iso,
            "finished_at": started_iso,
            "mode": mode,
            "touch_slugs": touch_slugs or [],
        }
        _last_result = result
        _write_status({**result, "running": False})
        logger.warning("prerender skip: %s", result["message"])
        return result

    index = web_root / "dist" / "index.html"
    if not index.is_file():
        result = {
            "ok": False,
            "message": f"missing {index} — run vite build once before prerender-on-publish",
            "started_at": started_iso,
            "finished_at": started_iso,
            "mode": mode,
            "touch_slugs": touch_slugs or [],
        }
        _last_result = result
        _write_status({**result, "running": False}, web_root)
        logger.warning("prerender skip: %s", result["message"])
        return result

    cmd = [_node_bin(), "scripts/prerender.mjs"]
    env = _build_env(web_root, touch_slugs=touch_slugs)
    log_file = _log_path(web_root)
    _last_started_at = time.time()
    logger.info(
        "prerender start reason=%s mode=%s cwd=%s api=%s node=%s",
        reason,
        mode,
        web_root,
        env.get("VITE_API_BASE_URL"),
        cmd[0],
    )
    _write_status(
        {
            "ok": None,
            "message": f"running ({reason}, {mode})",
            "running": True,
            "started_at": started_iso,
            "mode": mode,
            "touch_slugs": touch_slugs or [],
            "pid": os.getpid(),
            "log": str(log_file),
            "api": env.get("VITE_API_BASE_URL"),
        },
        web_root,
    )

    exit_code: int | None = None
    try:
        with open(log_file, "a", encoding="utf-8") as fh:
            fh.write(
                f"\n--- {started_iso} reason={reason} mode={mode} "
                f"api={env.get('VITE_API_BASE_URL')} ---\n"
            )
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
        exit_code = proc.returncode
        if proc.returncode == 0:
            result = {
                "ok": True,
                "message": f"prerender ok ({reason}, {mode})",
                "log": str(log_file),
                "exit_code": 0,
            }
        else:
            result = {
                "ok": False,
                "message": f"prerender exit {proc.returncode} ({reason}, {mode})",
                "log": str(log_file),
                "exit_code": proc.returncode,
            }
            logger.error("prerender failed: %s", result["message"])
    except FileNotFoundError:
        result = {
            "ok": False,
            "message": f"node not found ({cmd[0]}) — set NODE_BIN or fix PATH for API service",
            "log": str(log_file),
            "exit_code": 127,
        }
        logger.error(result["message"])
    except subprocess.TimeoutExpired:
        result = {
            "ok": False,
            "message": f"prerender timeout ({reason})",
            "log": str(log_file),
            "exit_code": -1,
        }
        logger.error(result["message"])
    except Exception as e:
        result = {
            "ok": False,
            "message": f"prerender error: {e}",
            "log": str(log_file),
            "exit_code": -2,
        }
        logger.exception("prerender exception")

    finished_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    result.update(
        {
            "started_at": started_iso,
            "finished_at": finished_iso,
            "mode": mode,
            "touch_slugs": touch_slugs or [],
            "pid": os.getpid(),
        }
    )

    if result.get("ok") and touch_slugs:
        verify = _verify_touch_slugs(web_root, touch_slugs, env.get("SITE_URL") or "https://9well.com")
        result["verify"] = verify
        if not verify["ok"]:
            result["ok"] = False
            result["message"] = f"prerender wrote but verify failed: {verify['message']}"
            logger.error(result["message"])

    _last_result = result
    _write_status({**result, "running": False, "exit_code": exit_code if exit_code is not None else result.get("exit_code")}, web_root)
    return result


def _worker(reason: str, touch_slugs: list[str] | None) -> None:
    global _running, _queued, _queued_slugs
    try:
        while True:
            _run_once(reason, touch_slugs=touch_slugs)
            with _lock:
                if not _queued:
                    _running = False
                    _queued_slugs.clear()
                    return
                _queued = False
                touch_slugs = sorted(_queued_slugs) or None
                _queued_slugs.clear()
                reason = "queued-rerun"
    except Exception:
        logger.exception("prerender worker crashed")
        with _lock:
            _running = False
            _queued = False
            _queued_slugs.clear()
        _write_status(
            {
                "ok": False,
                "message": "prerender worker crashed",
                "running": False,
                "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )


def schedule_web_prerender(
    reason: str = "cms",
    touch_slugs: list[str] | None = None,
) -> dict[str, Any]:
    """Schedule background prerender. Safe to call from request handlers."""
    if not prerender_enabled():
        out = {"ok": False, "message": "PRERENDER_ON_PUBLISH disabled", "started": False}
        _write_status({**out, "running": False, "reason": reason})
        return out

    web_root = resolve_web_root()
    if not web_root:
        out = {
            "ok": False,
            "message": "CMS_WEB_ROOT not set / prerender.mjs not found",
            "started": False,
        }
        _write_status({**out, "running": False, "reason": reason})
        return out

    index = web_root / "dist" / "index.html"
    if not index.is_file():
        out = {
            "ok": False,
            "message": f"missing {index} — run vite build once before prerender-on-publish",
            "started": False,
        }
        _write_status({**out, "running": False, "reason": reason}, web_root)
        return out

    slugs = list(touch_slugs or [])
    parsed = _slug_from_reason(reason)
    if parsed and parsed not in slugs:
        slugs.append(parsed)

    global _running, _queued
    with _lock:
        if slugs:
            _queued_slugs.update(slugs)
        if _running:
            _queued = True
            out = {
                "ok": True,
                "message": "prerender already running — queued rerun",
                "started": False,
                "queued": True,
                "queued_slugs": sorted(_queued_slugs),
            }
            return out
        _running = True
        run_slugs = sorted(_queued_slugs) if _queued_slugs else None
        _queued_slugs.clear()

    threading.Thread(
        target=_worker,
        args=(reason, run_slugs),
        name="web-prerender",
        daemon=True,
    ).start()
    mode = f"touch={','.join(run_slugs)}" if run_slugs else "full"
    out = {"ok": True, "message": f"prerender started ({mode})", "started": True, "mode": mode}
    _write_status(
        {
            "ok": None,
            "message": out["message"],
            "running": True,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "mode": mode,
            "touch_slugs": run_slugs or [],
            "pid": os.getpid(),
        },
        web_root,
    )
    return out
