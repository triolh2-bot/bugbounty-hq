from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from flask import current_app, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .db import session_scope
from .models import IntegrationEvent
from .security import log_security_event
from .validation import ValidationError


logger = logging.getLogger(__name__)
_SIGNATURE_PREFIX_RE = re.compile(r"^(?:sha256|v1|sig)=(.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class WebhookProviderConfig:
    name: str
    secret: str | None
    signature_header: str
    timestamp_header: str
    event_id_header: str
    event_type_header: str | None = None


def _provider_name(provider: str) -> str:
    return provider.strip().lower()


def get_provider_config(provider: str) -> WebhookProviderConfig:
    provider_key = _provider_name(provider)
    provider_configs = current_app.config.get("WEBHOOK_PROVIDERS") or {}
    raw_config = provider_configs.get(provider_key)
    if raw_config is None:
        raise ValidationError("Webhook provider is not configured.", status_code=404)

    return WebhookProviderConfig(
        name=provider_key,
        secret=(raw_config.get("secret") or None),
        signature_header=str(raw_config["signature_header"]),
        timestamp_header=str(raw_config["timestamp_header"]),
        event_id_header=str(raw_config["event_id_header"]),
        event_type_header=raw_config.get("event_type_header") or None,
    )


def _read_request_body() -> bytes:
    raw_body = request.get_data(cache=True, as_text=False)
    max_body_size = int(current_app.config["WEBHOOK_MAX_BODY_BYTES"])
    if len(raw_body) > max_body_size:
        raise ValidationError(
            "Webhook payload is too large.",
            status_code=413,
        )
    return raw_body


def _request_headers_snapshot(provider_config: WebhookProviderConfig) -> dict[str, str | None]:
    headers: dict[str, str | None] = {
        "content_type": request.headers.get("Content-Type"),
        "user_agent": request.headers.get("User-Agent"),
        "remote_addr": request.remote_addr,
        "signature_header": request.headers.get(provider_config.signature_header),
        "timestamp_header": request.headers.get(provider_config.timestamp_header),
        "event_id_header": request.headers.get(provider_config.event_id_header),
    }
    if provider_config.event_type_header:
        headers["event_type_header"] = request.headers.get(provider_config.event_type_header)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        headers["x_forwarded_for"] = forwarded_for
    return {key: value for key, value in headers.items() if value is not None}


def _normalize_signature(value: str) -> str:
    normalized = value.strip()
    match = _SIGNATURE_PREFIX_RE.match(normalized)
    if match:
        normalized = match.group(1).strip()
    return normalized.lower()


def _parse_timestamp(value: str) -> tuple[int, datetime]:
    try:
        timestamp = int(value.strip())
    except (TypeError, ValueError) as exc:
        raise ValidationError("Webhook timestamp is invalid.") from exc

    return timestamp, datetime.fromtimestamp(timestamp, tz=timezone.utc)


def _signature_payload(timestamp_value: str, raw_body: bytes) -> bytes:
    return f"{timestamp_value}.".encode("utf-8") + raw_body


def _event_payload(raw_body: bytes) -> dict[str, Any]:
    try:
        decoded = raw_body.decode("utf-8")
        payload = json.loads(decoded)
    except UnicodeDecodeError as exc:
        raise ValidationError("Webhook payload must be UTF-8 encoded JSON.") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError("Webhook payload must be valid JSON.") from exc

    if not isinstance(payload, dict):
        raise ValidationError("Webhook payload must be a JSON object.")
    return payload


def _first_non_empty(*values: object) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _payload_identity(provider: str, payload: dict[str, Any], body_hash: str) -> tuple[str, str | None, str | None]:
    provider_config = get_provider_config(provider)
    external_event_id = _first_non_empty(
        request.headers.get(provider_config.event_id_header),
        payload.get("event_id"),
        payload.get("id"),
        payload.get("delivery_id"),
        payload.get("uuid"),
    )
    event_type = _first_non_empty(
        request.headers.get(provider_config.event_type_header)
        if provider_config.event_type_header
        else None,
        payload.get("event_type"),
        payload.get("type"),
        payload.get("action"),
    )
    dedupe_key = f"{_provider_name(provider)}:{external_event_id or body_hash}"
    return dedupe_key, external_event_id, event_type


def _record_event(
    *,
    provider_config: WebhookProviderConfig,
    raw_body: bytes,
    timestamp_header_value: str | None,
    signature_value: str | None,
    dedupe_key: str,
    external_event_id: str | None,
    event_type: str | None,
    payload: dict[str, Any] | None,
    status: str,
    failure_reason: str | None = None,
    processed_at: datetime | None = None,
    dead_lettered_at: datetime | None = None,
) -> IntegrationEvent:
    body_hash = hashlib.sha256(raw_body).hexdigest()
    headers_snapshot = _request_headers_snapshot(provider_config)
    payload_text = json.dumps(payload, sort_keys=True) if payload is not None else None
    return IntegrationEvent(
        id=str(uuid.uuid4()),
        provider=provider_config.name,
        external_event_id=external_event_id,
        dedupe_key=dedupe_key,
        event_type=event_type,
        signature=signature_value,
        timestamp_header=timestamp_header_value,
        payload_hash=body_hash,
        raw_body=raw_body.decode("utf-8", errors="replace"),
        headers_json=json.dumps(headers_snapshot, sort_keys=True),
        payload_json=payload_text,
        status=status,
        failure_reason=failure_reason,
        processed_at=processed_at,
        dead_lettered_at=dead_lettered_at,
    )


def _store_event(event: IntegrationEvent) -> IntegrationEvent:
    with session_scope() as session:
        existing = session.scalar(
            select(IntegrationEvent).where(IntegrationEvent.dedupe_key == event.dedupe_key)
        )
        if existing is not None:
            return existing

        session.add(event)
        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            existing = session.scalar(
                select(IntegrationEvent).where(
                    IntegrationEvent.dedupe_key == event.dedupe_key
                )
            )
            if existing is not None:
                return existing
            raise
        return event


def _reject_event(
    *,
    provider_config: WebhookProviderConfig,
    raw_body: bytes,
    timestamp_header_value: str | None,
    signature_value: str | None,
    failure_reason: str,
    status_code: int,
) -> None:
    body_hash = hashlib.sha256(raw_body).hexdigest()
    event = _record_event(
        provider_config=provider_config,
        raw_body=raw_body,
        timestamp_header_value=timestamp_header_value,
        signature_value=signature_value,
        dedupe_key=f"{provider_config.name}:{body_hash}",
        external_event_id=None,
        event_type=None,
        payload=None,
        status="dead_lettered",
        failure_reason=failure_reason,
        dead_lettered_at=datetime.utcnow(),
    )
    _store_event(event)
    log_security_event(f"webhook_{provider_config.name}", outcome="rejected", detail=failure_reason)
    raise ValidationError(failure_reason, status_code=status_code)


def verify_incoming_webhook(provider: str) -> dict[str, object]:
    provider_config = get_provider_config(provider)
    raw_body = _read_request_body()
    timestamp_header_value = request.headers.get(provider_config.timestamp_header)
    signature_header_value = request.headers.get(provider_config.signature_header)

    if not provider_config.secret:
        _reject_event(
            provider_config=provider_config,
            raw_body=raw_body,
            timestamp_header_value=timestamp_header_value,
            signature_value=signature_header_value,
            failure_reason="Webhook provider is not configured.",
            status_code=503,
        )

    if not timestamp_header_value:
        _reject_event(
            provider_config=provider_config,
            raw_body=raw_body,
            timestamp_header_value=None,
            signature_value=signature_header_value,
            failure_reason="Webhook timestamp header is required.",
            status_code=400,
        )

    if not signature_header_value:
        _reject_event(
            provider_config=provider_config,
            raw_body=raw_body,
            timestamp_header_value=timestamp_header_value,
            signature_value=None,
            failure_reason="Webhook signature header is required.",
            status_code=401,
        )

    try:
        _timestamp_value, timestamp_dt = _parse_timestamp(timestamp_header_value)
    except ValidationError as exc:
        _reject_event(
            provider_config=provider_config,
            raw_body=raw_body,
            timestamp_header_value=timestamp_header_value,
            signature_value=signature_header_value,
            failure_reason=exc.message,
            status_code=exc.status_code,
        )

    now = datetime.now(tz=timezone.utc)
    skew_seconds = int(current_app.config["WEBHOOK_TIMESTAMP_SKEW_SECONDS"])
    replay_window_seconds = int(current_app.config["WEBHOOK_REPLAY_WINDOW_SECONDS"])
    allowed_replay_window = min(skew_seconds, replay_window_seconds)
    if abs((now - timestamp_dt).total_seconds()) > allowed_replay_window:
        _reject_event(
            provider_config=provider_config,
            raw_body=raw_body,
            timestamp_header_value=timestamp_header_value,
            signature_value=signature_header_value,
            failure_reason="Webhook timestamp is outside the accepted replay window.",
            status_code=403,
        )

    expected_signature = hmac.new(
        provider_config.secret.encode("utf-8"),
        _signature_payload(timestamp_header_value, raw_body),
        hashlib.sha256,
    ).hexdigest()
    provided_signature = _normalize_signature(signature_header_value)
    if not hmac.compare_digest(expected_signature, provided_signature):
        _reject_event(
            provider_config=provider_config,
            raw_body=raw_body,
            timestamp_header_value=timestamp_header_value,
            signature_value=provided_signature,
            failure_reason="Webhook signature is invalid.",
            status_code=401,
        )

    try:
        payload = _event_payload(raw_body)
    except ValidationError as exc:
        _reject_event(
            provider_config=provider_config,
            raw_body=raw_body,
            timestamp_header_value=timestamp_header_value,
            signature_value=provided_signature,
            failure_reason=exc.message,
            status_code=exc.status_code,
        )

    body_hash = hashlib.sha256(raw_body).hexdigest()
    dedupe_key, external_event_id, event_type = _payload_identity(provider, payload, body_hash)

    event = _record_event(
        provider_config=provider_config,
        raw_body=raw_body,
        timestamp_header_value=timestamp_header_value,
        signature_value=provided_signature,
        dedupe_key=dedupe_key,
        external_event_id=external_event_id,
        event_type=event_type,
        payload=payload,
        status="accepted",
    )

    stored_event = _store_event(event)
    is_duplicate = stored_event.id != event.id
    outcome = "duplicate" if is_duplicate else "accepted"
    log_security_event(
        f"webhook_{provider_config.name}",
        outcome=outcome,
        detail=stored_event.dedupe_key,
    )

    return {
        "accepted": not is_duplicate,
        "duplicate": is_duplicate,
        "event": stored_event.to_dict(),
    }
