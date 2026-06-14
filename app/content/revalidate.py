from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_PATHS = ["/", "/blog", "/lieu-trinh", "/khoa-hoc", "/chuyen-gia", "/quiz"]


def trigger_revalidate(paths: list[str] | None = None) -> dict[str, Any]:
    secret = os.environ.get("REVALIDATE_SECRET", "")
    base_url = os.environ.get("VERCEL_REVALIDATE_URL", os.environ.get("NEXT_REVALIDATE_URL", ""))
    target_paths = paths or DEFAULT_PATHS

    if not secret or not base_url:
        return {"ok": False, "revalidated": [], "message": "Revalidate not configured"}

    url = base_url.rstrip("/") + "/api/revalidate"

    try:
        resp = httpx.post(
            url,
            json={"paths": target_paths},
            headers={"X-Revalidate-Secret": secret},
            timeout=15.0,
        )
        if resp.status_code < 300:
            data = resp.json() if resp.content else {}
            revalidated = list(data.get("revalidated") or target_paths)
            return {"ok": True, "revalidated": revalidated, "message": "Revalidated"}
        return {"ok": False, "revalidated": [], "message": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"ok": False, "revalidated": [], "message": str(e)}
