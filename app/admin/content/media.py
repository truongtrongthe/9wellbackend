from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from supabase import Client

from app.admin.deps import AdminContext, require_admin
from app.config import get_settings
from app.db.supabase_client import get_supabase

router = APIRouter(prefix="/media", tags=["admin-content-media"])

ALLOWED = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_BYTES = 5 * 1024 * 1024


@router.post("")
async def upload_media(
    file: Annotated[UploadFile, File()],
    _admin: AdminContext = Depends(require_admin),
    client: Client = Depends(get_supabase),
) -> dict[str, str]:
    content_type = file.content_type or ""
    if content_type not in ALLOWED:
        raise HTTPException(status_code=400, detail="Only jpeg/png/webp/gif allowed")

    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="Max file size 5MB")

    ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}.get(
        content_type, "bin"
    )
    path = f"{uuid.uuid4().hex}.{ext}"
    bucket = "cms-media"

    client.storage.from_(bucket).upload(
        path,
        data,
        file_options={"content-type": content_type, "upsert": "false"},
    )

    settings = get_settings()
    base = str(settings.supabase_url).rstrip("/")
    url = f"{base}/storage/v1/object/public/{bucket}/{path}"
    return {"url": url}
