import os
from datetime import timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DEVELOPMENT_SECRET = "dev-secret-key-change-me"
DEFAULT_TESTING_SECRET = "testing-secret-key-change-me"
MIN_SECRET_KEY_LENGTH = 32
NON_PRODUCTION_ENVIRONMENTS = {"dev", "development", "test", "testing"}
PRODUCTION_PLACEHOLDER_SECRETS = {
    "",
    "bugbounty-secret-key-change-me",
    "change-me",
    "dev-secret-key-change-me",
    "testing-secret-key-change-me",
    "your-secret-key-here",
    "your-production-secret-key",
}


def _normalize_secret(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None
    normalized = raw_value.strip()
    return normalized or None


def _build_webhook_provider(
    *,
    secret: str | None,
    signature_header: str,
    timestamp_header: str,
    event_id_header: str,
    event_type_header: str | None = None,
) -> dict[str, object]:
    provider_config: dict[str, object] = {
        "secret": secret,
        "signature_header": signature_header,
        "timestamp_header": timestamp_header,
        "event_id_header": event_id_header,
    }
    if event_type_header is not None:
        provider_config["event_type_header"] = event_type_header
    return provider_config


def build_webhook_provider_configs() -> dict[str, dict[str, object]]:
    default_secret = _normalize_secret(
        os.environ.get("BUGBOUNTYHQ_WEBHOOK_DEFAULT_SECRET")
    )

    return {
        "hackerone": _build_webhook_provider(
            secret=_normalize_secret(
                os.environ.get("BUGBOUNTYHQ_WEBHOOK_HACKERONE_SECRET")
            )
            or default_secret,
            signature_header="X-HackerOne-Signature",
            timestamp_header="X-HackerOne-Timestamp",
            event_id_header="X-HackerOne-Event-Id",
            event_type_header="X-HackerOne-Event-Type",
        ),
        "bugcrowd": _build_webhook_provider(
            secret=_normalize_secret(
                os.environ.get("BUGBOUNTYHQ_WEBHOOK_BUGCROWD_SECRET")
            )
            or default_secret,
            signature_header="X-Bugcrowd-Signature",
            timestamp_header="X-Bugcrowd-Timestamp",
            event_id_header="X-Bugcrowd-Event-Id",
            event_type_header="X-Bugcrowd-Event-Type",
        ),
    }


def normalize_database_url(raw_value: str | None) -> str:
    if not raw_value:
        raw_value = str(BASE_DIR / "bugbounty.db")

    if "://" in raw_value:
        return raw_value

    path = Path(raw_value)
    if not path.is_absolute():
        path = BASE_DIR / path

    return f"sqlite:///{path.resolve().as_posix()}"


def get_environment() -> str:
    return os.environ.get("BUGBOUNTYHQ_ENV", os.environ.get("FLASK_ENV", "development")).lower()


def build_config(overrides: dict[str, object] | None = None) -> dict[str, object]:
    overrides = overrides or {}
    env = get_environment()
    config: dict[str, object] = {
        "BUGBOUNTYHQ_ENV": env,
        "JSON_SORT_KEYS": False,
        "PERMANENT_SESSION_LIFETIME": timedelta(hours=8),
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_REFRESH_EACH_REQUEST": True,
        "RATE_LIMIT_WINDOW_SECONDS": 60,
        "RATE_LIMIT_LOGIN_ATTEMPTS": 5,
        "RATE_LIMIT_WEBHOOK_REQUESTS": 30,
        "RATE_LIMIT_SUBMISSION_CREATES": 10,
        "WEBHOOK_MAX_BODY_BYTES": int(
            os.environ.get("BUGBOUNTYHQ_WEBHOOK_MAX_BODY_BYTES", "262144")
        ),
        "WEBHOOK_TIMESTAMP_SKEW_SECONDS": int(
            os.environ.get("BUGBOUNTYHQ_WEBHOOK_TIMESTAMP_SKEW_SECONDS", "300")
        ),
        "WEBHOOK_REPLAY_WINDOW_SECONDS": int(
            os.environ.get("BUGBOUNTYHQ_WEBHOOK_REPLAY_WINDOW_SECONDS", "86400")
        ),
        "WEBHOOK_IDEMPOTENCY_WINDOW_SECONDS": int(
            os.environ.get("BUGBOUNTYHQ_WEBHOOK_IDEMPOTENCY_WINDOW_SECONDS", "86400")
        ),
        "WEBHOOK_PROVIDERS": build_webhook_provider_configs(),
        "SECURITY_HEADER_HSTS_SECONDS": 31536000,
        "SECURITY_HEADER_CSP": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        ),
        "DATABASE_URL": normalize_database_url(
            os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_PATH")
        ),
    }

    if env in {"test", "testing"}:
        config["TESTING"] = True
        config["SECRET_KEY"] = os.environ.get("SECRET_KEY", DEFAULT_TESTING_SECRET)
        config["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
        config["SESSION_COOKIE_SECURE"] = False
    elif env in {"dev", "development"}:
        config["DEBUG"] = True
        config["SECRET_KEY"] = os.environ.get("SECRET_KEY", DEFAULT_DEVELOPMENT_SECRET)
        config["SESSION_COOKIE_SECURE"] = False
    else:
        config["DEBUG"] = False
        config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
        config["SESSION_COOKIE_SECURE"] = True

    config.update(overrides)

    effective_env = str(config.get("BUGBOUNTYHQ_ENV", env)).lower()
    if config.get("TESTING") or effective_env in {"test", "testing"}:
        config["TESTING"] = True
        config["BUGBOUNTYHQ_ENV"] = "testing"
        if "SECRET_KEY" not in overrides:
            config["SECRET_KEY"] = os.environ.get("SECRET_KEY", DEFAULT_TESTING_SECRET)
        if "DATABASE_URL" not in overrides:
            config["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
        if "SESSION_COOKIE_SECURE" not in overrides:
            config["SESSION_COOKIE_SECURE"] = False

    return config


def is_production_environment(config: dict[str, object]) -> bool:
    if config.get("TESTING"):
        return False

    env = str(config.get("BUGBOUNTYHQ_ENV", "production")).lower()
    return env not in NON_PRODUCTION_ENVIRONMENTS


def validate_config(config: dict[str, object]) -> None:
    if config.get("TESTING"):
        return

    if not is_production_environment(config):
        return

    secret_key = str(config.get("SECRET_KEY") or "")

    if config.get("DEBUG"):
        raise RuntimeError("DEBUG must be disabled in production")

    if not secret_key:
        raise RuntimeError(
            "SECRET_KEY is required when BUGBOUNTYHQ_ENV=production"
        )

    if len(secret_key) < MIN_SECRET_KEY_LENGTH:
        raise RuntimeError(
            "SECRET_KEY must be at least 32 characters in production"
        )

    if secret_key in PRODUCTION_PLACEHOLDER_SECRETS:
        raise RuntimeError(
            "SECRET_KEY is using a placeholder value; set a random production secret"
        )

    for provider_name, provider_config in (
        config.get("WEBHOOK_PROVIDERS") or {}
    ).items():
        secret = str(provider_config.get("secret") or "")
        if not secret:
            continue
        if len(secret) < MIN_SECRET_KEY_LENGTH:
            raise RuntimeError(
                f"Webhook secret for {provider_name} must be at least 32 characters in production"
            )
        if secret in PRODUCTION_PLACEHOLDER_SECRETS:
            raise RuntimeError(
                f"Webhook secret for {provider_name} is using a placeholder value"
            )
