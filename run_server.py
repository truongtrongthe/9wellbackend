"""Run the API from the repo root so the `app` package resolves correctly."""

from __future__ import annotations

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
