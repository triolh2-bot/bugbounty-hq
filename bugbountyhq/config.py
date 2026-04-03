import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def normalize_database_url(raw_value: str | None) -> str:
    if not raw_value:
        raw_value = str(BASE_DIR / "bugbounty.db")

    if "://" in raw_value:
        return raw_value

    path = Path(raw_value)
    if not path.is_absolute():
        path = BASE_DIR / path

    return f"sqlite:///{path.resolve().as_posix()}"


_normalize_database_url = normalize_database_url


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "bugbounty-secret-key-change-me")
    DATABASE_URL = normalize_database_url(
        os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_PATH")
    )
    JSON_SORT_KEYS = False


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    DATABASE_URL = "sqlite+pysqlite:///:memory:"


class ProductionConfig(BaseConfig):
    pass


def get_config():
    env = os.environ.get("BUGBOUNTYHQ_ENV", os.environ.get("FLASK_ENV", "production")).lower()
    if env in {"dev", "development"}:
        return DevelopmentConfig
    if env in {"test", "testing"}:
        return TestingConfig
    return ProductionConfig
