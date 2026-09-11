from __future__ import annotations

import os

from app.content.prerender_trigger import prerender_enabled, schedule_web_prerender


def test_prerender_respects_disable(monkeypatch):
    monkeypatch.setenv("PRERENDER_ON_PUBLISH", "0")
    assert prerender_enabled() is False
    out = schedule_web_prerender("unit-test")
    assert out["started"] is False
    assert "disabled" in out["message"].lower() or out["ok"] is False


def test_prerender_enable_flag(monkeypatch):
    monkeypatch.setenv("PRERENDER_ON_PUBLISH", "1")
    assert prerender_enabled() is True
