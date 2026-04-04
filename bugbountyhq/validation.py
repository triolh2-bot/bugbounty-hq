from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ValidationError(Exception):
    message: str
    field: str | None = None
    status_code: int = 400


def require_text(data, field: str, label: str | None = None) -> str:
    value = data.get(field)
    if value is None:
        raise ValidationError(f"{label or field} is required.", field=field)

    normalized = str(value).strip()
    if not normalized:
        raise ValidationError(f"{label or field} is required.", field=field)
    return normalized


def optional_text(data, field: str) -> str | None:
    value = data.get(field)
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def require_choice(data, field: str, choices: set[str], label: str | None = None) -> str:
    value = require_text(data, field, label=label)
    if value not in choices:
        raise ValidationError(f"{label or field} is invalid.", field=field)
    return value


def optional_money(data, field: str) -> float | None:
    raw_value = data.get(field)
    if raw_value in (None, ""):
        return None

    try:
        value = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field} must be a valid number.", field=field) from exc

    if value < 0:
        raise ValidationError(f"{field} must be zero or greater.", field=field)

    return value


def require_json_body(payload):
    if payload is None:
        raise ValidationError("Request body must be valid JSON.")
    return payload
