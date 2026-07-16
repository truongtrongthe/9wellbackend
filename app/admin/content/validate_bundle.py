from __future__ import annotations

from typing import Any


def validate_bundle_payload(key: str, payload: Any) -> list[str]:
    """Return list of validation errors (empty = ok)."""
    errors: list[str] = []
    if payload is None:
        errors.append("payload is null")
        return errors
    if not isinstance(payload, dict) and key not in ("hub_videos",):
        if isinstance(payload, list) and key == "hub_videos":
            return errors
        if not isinstance(payload, dict):
            errors.append("payload must be an object")
            return errors

    if key == "learn_curriculum":
        errors.extend(_validate_learn(payload))
    elif key == "shop_catalog":
        errors.extend(_validate_shop(payload))
    elif key == "portal_app":
        errors.extend(_validate_portal(payload))
    elif key == "landing_copy":
        if not isinstance(payload.get("hero"), dict):
            errors.append("landing_copy.hero should be an object")
    elif key == "legal_pages":
        for field in ("medical", "privacy", "terms"):
            if field in payload and payload[field] is not None and not isinstance(payload[field], str):
                errors.append(f"legal_pages.{field} must be a string")
    elif key == "hub_videos":
        vids = payload.get("videos") if isinstance(payload, dict) else payload
        if vids is not None and not isinstance(vids, list):
            errors.append("hub_videos.videos must be an array")

    return errors


def _validate_learn(p: dict) -> list[str]:
    errors: list[str] = []
    weeks = p.get("NW_WEEKS")
    if weeks is None:
        errors.append("NW_WEEKS is required")
    elif not isinstance(weeks, list):
        errors.append("NW_WEEKS must be an array")
    else:
        for i, w in enumerate(weeks):
            if not isinstance(w, dict):
                errors.append(f"NW_WEEKS[{i}] must be an object")
                continue
            if w.get("n") is None:
                errors.append(f"NW_WEEKS[{i}].n (week number) is required")
            lessons = w.get("lessons")
            if lessons is not None and not isinstance(lessons, list):
                errors.append(f"NW_WEEKS[{i}].lessons must be an array")
            elif isinstance(lessons, list):
                for j, les in enumerate(lessons):
                    if not isinstance(les, dict):
                        errors.append(f"NW_WEEKS[{i}].lessons[{j}] must be an object")
                    elif not les.get("id"):
                        errors.append(f"NW_WEEKS[{i}].lessons[{j}].id is required")
                    elif not les.get("fmt"):
                        errors.append(f"NW_WEEKS[{i}].lessons[{j}].fmt is required")
    checkins = p.get("NW_CHECKINS")
    if checkins is not None and not isinstance(checkins, dict):
        errors.append("NW_CHECKINS must be an object keyed by week number")
    summary = p.get("NW_SUMMARY")
    if summary is not None and not isinstance(summary, dict):
        errors.append("NW_SUMMARY must be an object")
    elif isinstance(summary, dict):
        qs = summary.get("questions")
        if qs is not None and not isinstance(qs, list):
            errors.append("NW_SUMMARY.questions must be an array")
    return errors


def _validate_shop(p: dict) -> list[str]:
    errors: list[str] = []
    products = p.get("products")
    if products is not None and not isinstance(products, list):
        errors.append("products must be an array")
    elif isinstance(products, list):
        for i, pr in enumerate(products):
            if not isinstance(pr, dict):
                errors.append(f"products[{i}] must be an object")
            elif not pr.get("id"):
                errors.append(f"products[{i}].id is required")
            elif not pr.get("name"):
                errors.append(f"products[{i}].name is required")
    return errors


def _validate_portal(p: dict) -> list[str]:
    errors: list[str] = []
    for field in ("plans", "quiz", "weeks"):
        val = p.get(field)
        if val is not None and not isinstance(val, list):
            errors.append(f"{field} must be an array")
    return errors
