from __future__ import annotations

import logging
import time
from collections import deque
from functools import wraps

from flask import request

from .auth import current_user
from .validation import ValidationError


logger = logging.getLogger(__name__)
_RATE_LIMIT_BUCKETS: dict[str, deque[float]] = {}


def _client_key(scope: str, identifier: str | None = None) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    client_ip = forwarded_for.split(",")[0].strip() or request.remote_addr or "unknown"
    suffix = identifier or client_ip
    return f"{scope}:{client_ip}:{suffix}"


def enforce_rate_limit(
    scope: str, limit: int, window_seconds: int, *, identifier: str | None = None
) -> None:
    now = time.time()
    bucket = _RATE_LIMIT_BUCKETS.setdefault(_client_key(scope, identifier), deque())

    while bucket and now - bucket[0] > window_seconds:
        bucket.popleft()

    if len(bucket) >= limit:
        raise ValidationError(
            "Too many requests. Please wait and try again.",
            status_code=429,
        )

    bucket.append(now)


def rate_limit(scope: str, limit: int, window_seconds: int, *, identifier: str | None = None):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            enforce_rate_limit(scope, limit, window_seconds, identifier=identifier)
            return view_func(*args, **kwargs)

        return wrapped_view

    return decorator


def log_security_event(action: str, *, outcome: str, detail: str | None = None) -> None:
    user = current_user()
    logger.info(
        "security_event action=%s outcome=%s user_id=%s email=%s path=%s detail=%s",
        action,
        outcome,
        getattr(user, "id", None),
        getattr(user, "email", None),
        request.path,
        detail,
    )


def register_security_observers(app) -> None:
    @app.after_request
    def add_rate_limit_header(response):
        if response.status_code == 429:
            response.headers.setdefault("Retry-After", str(app.config["RATE_LIMIT_WINDOW_SECONDS"]))
        return response
