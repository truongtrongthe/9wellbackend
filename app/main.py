from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.membership.router import router as membership_router
from app.payments.momo.router import router as momo_router
from app.roadmap.router import router as roadmap_router
from app.admin.router import router as admin_router
from app.content.router import router as public_content_router


def _cors_origins() -> list[str]:
    origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]
    extra = os.environ.get("CORS_ORIGINS", "")
    if extra:
        origins.extend(x.strip() for x in extra.split(",") if x.strip())
    origins.extend(["https://admin.9well.com", "https://9well.com"])
    return origins


def create_app() -> FastAPI:
    app = FastAPI(title="9wellbackend", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(membership_router, prefix="/membership", tags=["membership"])
    app.include_router(momo_router, tags=["payments"])
    app.include_router(roadmap_router, prefix="/roadmap", tags=["roadmap"])
    app.include_router(admin_router, prefix="/admin", tags=["admin"])
    app.include_router(public_content_router, prefix="/content", tags=["content"])

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

