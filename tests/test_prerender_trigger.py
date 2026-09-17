from __future__ import annotations

import json
from pathlib import Path

from app.content.prerender_trigger import (
    prerender_enabled,
    prerender_status,
    schedule_web_prerender,
)


def test_prerender_respects_disable(monkeypatch):
    monkeypatch.setenv("PRERENDER_ON_PUBLISH", "0")
    assert prerender_enabled() is False
    out = schedule_web_prerender("unit-test")
    assert out["started"] is False
    assert "disabled" in out["message"].lower() or out["ok"] is False


def test_prerender_enable_flag(monkeypatch):
    monkeypatch.setenv("PRERENDER_ON_PUBLISH", "1")
    assert prerender_enabled() is True


def test_prerender_missing_root_writes_status(monkeypatch, tmp_path):
    monkeypatch.setenv("PRERENDER_ON_PUBLISH", "1")
    monkeypatch.setenv("CMS_WEB_ROOT", str(tmp_path / "missing-web"))
    monkeypatch.setenv("PRERENDER_STATUS_FILE", str(tmp_path / "status.json"))
    out = schedule_web_prerender("unit-missing-root")
    assert out["started"] is False
    assert out["ok"] is False
    status = json.loads(Path(tmp_path / "status.json").read_text())
    assert status["ok"] is False
    assert "prerender.mjs" in status["message"] or "not found" in status["message"].lower()


def test_prerender_status_shape(monkeypatch, tmp_path):
    monkeypatch.setenv("PRERENDER_ON_PUBLISH", "0")
    monkeypatch.setenv("PRERENDER_STATUS_FILE", str(tmp_path / "status.json"))
    st = prerender_status()
    assert "enabled" in st
    assert "running" in st
    assert "last_result" in st
    assert "web_root" in st
