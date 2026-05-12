from __future__ import annotations

from typing import Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from app.auth.security import get_current_user
from app.db.supabase_client import get_supabase
from app.roadmap.logic import ModuleRow, compute_effective_statuses, validate_progress_patch
from app.roadmap.models import (
    AiGuidanceResponse,
    NoteCreate,
    NoteItem,
    ProgressPatchBody,
    RoadmapModuleItem,
    RoadmapResponse,
)
from app.roadmap.repository import (
    bootstrap_user_progress,
    create_note,
    ensure_default_ai_guidance,
    latest_ai_guidance,
    list_active_modules,
    list_notes,
    list_progress_for_user,
    update_progress_status,
)

router = APIRouter()


def _module_rows(modules: list[dict[str, Any]]) -> list[ModuleRow]:
    return [
        ModuleRow(id=str(m["id"]), sequence_order=int(m["sequence_order"]))
        for m in sorted(modules, key=lambda x: int(x["sequence_order"]))
    ]


def _stored_map(progress: list[dict[str, Any]]) -> dict[str, Literal["locked", "in_progress", "completed"]]:
    out: dict[str, Literal["locked", "in_progress", "completed"]] = {}
    for r in progress:
        s = str(r["status"])
        if s in ("locked", "in_progress", "completed"):
            out[str(r["module_id"])] = cast(Literal["locked", "in_progress", "completed"], s)
    return out


@router.get("", response_model=RoadmapResponse)
def get_roadmap(
    user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase),
) -> RoadmapResponse:
    uid = str(user["id"])
    modules = list_active_modules(client)
    rows = _module_rows(modules)
    bootstrap_user_progress(client, uid, modules)
    ensure_default_ai_guidance(client, uid)
    progress = list_progress_for_user(client, uid)
    stored = _stored_map(progress)
    effective = compute_effective_statuses(rows, stored)
    items: list[RoadmapModuleItem] = []
    for m in sorted(modules, key=lambda x: int(x["sequence_order"])):
        mid = str(m["id"])
        items.append(
            RoadmapModuleItem(
                id=mid,
                code=str(m["code"]),
                title=str(m["title"]),
                description=m.get("description"),
                sequenceOrder=int(m["sequence_order"]),
                status=effective[mid],
            )
        )
    return RoadmapResponse(modules=items)


@router.get("/ai-guidance", response_model=AiGuidanceResponse)
def get_ai_guidance(
    user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase),
) -> AiGuidanceResponse:
    row = latest_ai_guidance(client, str(user["id"]))
    if not row:
        return AiGuidanceResponse(message=None, source=None, createdAt=None)
    return AiGuidanceResponse(
        message=str(row["message"]),
        source=str(row.get("source") or "system"),
        createdAt=row.get("created_at"),
    )


@router.get("/notes", response_model=list[NoteItem])
def get_notes(
    user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[NoteItem]:
    rows = list_notes(client, str(user["id"]), limit=limit, offset=offset)
    return [
        NoteItem(
            id=str(r["id"]),
            content=str(r["content"]),
            createdAt=r["created_at"],
            updatedAt=r.get("updated_at"),
        )
        for r in rows
    ]


@router.post("/notes", response_model=NoteItem)
def post_note(
    body: NoteCreate,
    user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase),
) -> NoteItem:
    r = create_note(client, str(user["id"]), body.content)
    return NoteItem(
        id=str(r["id"]),
        content=str(r["content"]),
        createdAt=r["created_at"],
        updatedAt=r.get("updated_at"),
    )


@router.patch("/progress/{module_id}")
def patch_progress(
    module_id: str,
    body: ProgressPatchBody,
    user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase),
) -> dict[str, str]:
    uid = str(user["id"])
    modules = list_active_modules(client)
    rows = _module_rows(modules)
    bootstrap_user_progress(client, uid, modules)
    progress = list_progress_for_user(client, uid)
    stored = _stored_map(progress)
    err = validate_progress_patch(
        target_module_id=module_id,
        new_status=body.status,
        modules_sorted=rows,
        stored_by_module_id=stored,
    )
    if err:
        raise HTTPException(status_code=400, detail=err)
    update_progress_status(client, uid, module_id, body.status)
    if body.status == "completed":
        by_order = sorted(modules, key=lambda x: int(x["sequence_order"]))
        idx = next((i for i, m in enumerate(by_order) if str(m["id"]) == module_id), -1)
        if idx >= 0 and idx + 1 < len(by_order):
            nxt = str(by_order[idx + 1]["id"])
            if stored.get(nxt) == "locked":
                update_progress_status(client, uid, nxt, "in_progress")
    return {"status": "ok"}
