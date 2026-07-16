from __future__ import annotations

import os
from typing import Any

import httpx


def send_checkin_telegram(
    *,
    nickname: str,
    client_code: str,
    week_number: int,
    mood: str | None,
    freq: str | None,
    control: str | None,
    notes: str | None,
) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return False

    lines = [
        "📋 Check-in 9well him",
        f"Khách: {nickname} ({client_code})",
        f"Tuần: {week_number}",
        f"Tâm trạng: {mood or '—'}",
        f"Tần suất: {freq or '—'}",
        f"Tự chủ: {control or '—'}",
    ]
    if notes:
        lines.append(f"Ghi chú: {notes}")

    text = "\n".join(lines)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = httpx.post(url, json={"chat_id": chat_id, "text": text}, timeout=10.0)
        return r.is_success
    except Exception:
        return False


def send_shop_order_telegram(
    *,
    name: str,
    phone: str,
    address: str,
    note: str,
    total: int,
    items: list[dict[str, Any]],
) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return False

    item_lines = [
        f"• {it.get('name')} x{it.get('qty')} = {int(it.get('price', 0)) * int(it.get('qty', 1)):,}₫".replace(",", ".")
        for it in items
    ]
    lines = [
        "🛒 Đơn Shop 9well",
        f"Người nhận: {name} · {phone}",
        f"Địa chỉ: {address}",
        *item_lines,
        f"Tổng: {total:,}₫".replace(",", "."),
    ]
    if note:
        lines.append(f"Ghi chú: {note}")

    text = "\n".join(lines)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = httpx.post(url, json={"chat_id": chat_id, "text": text}, timeout=10.0)
        return r.is_success
    except Exception:
        return False
