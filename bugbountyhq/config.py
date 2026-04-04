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
