from pathlib import Path

from alembic import command
from alembic.config import Config
from flask import current_app
from sqlalchemy import inspect

from .db import create_engine_for_url
from .models import Base


def _alembic_config(database_url: str | None = None) -> Config:
    root_dir = Path(__file__).resolve().parent.parent
    config = Config(str(root_dir / "alembic.ini"))
    config.set_main_option("script_location", str(root_dir / "migrations"))
    if database_url is None:
        database_url = current_app.config["DATABASE_URL"]
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def upgrade_database(database_url: str | None = None) -> None:
    config = _alembic_config(database_url)
    engine = create_engine_for_url(config.get_main_option("sqlalchemy.url"))
    try:
        inspector = inspect(engine)

        domain_tables = [table_name for table_name in Base.metadata.tables]
        has_existing_domain_tables = all(
            inspector.has_table(table_name) for table_name in domain_tables
        )
        has_version_table = inspector.has_table("alembic_version")

        if has_existing_domain_tables and not has_version_table:
            command.stamp(config, "head")
            return

        command.upgrade(config, "head")
    finally:
        engine.dispose()


def stamp_database(database_url: str | None = None) -> None:
    command.stamp(_alembic_config(database_url), "head")
