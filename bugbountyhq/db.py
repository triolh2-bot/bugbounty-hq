from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from flask import Flask, current_app
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .models import Base


ENGINE_KEY = "bugbountyhq_engine"
SESSION_FACTORY_KEY = "bugbountyhq_session_factory"


def create_engine_for_url(database_url: str) -> Engine:
    engine_kwargs: dict[str, object] = {
        "future": True,
        "pool_pre_ping": True,
    }

    if database_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in database_url:
            engine_kwargs["poolclass"] = StaticPool

    engine = create_engine(database_url, **engine_kwargs)

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def init_db(app: Flask) -> None:
    database_url = app.config["DATABASE_URL"]
    engine = create_engine_for_url(database_url)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )

    app.extensions[ENGINE_KEY] = engine
    app.extensions[SESSION_FACTORY_KEY] = session_factory

    Base.metadata.create_all(bind=engine)

    register_db_commands(app)


def get_engine() -> Engine:
    return current_app.extensions[ENGINE_KEY]


def get_session_factory() -> sessionmaker:
    return current_app.extensions[SESSION_FACTORY_KEY]


def get_session() -> Session:
    return get_session_factory()()


@contextmanager
def session_scope() -> Iterator[Session]:
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def register_db_commands(app: Flask) -> None:
    @app.cli.command("db-upgrade")
    def db_upgrade() -> None:
        from .migrations import upgrade_database

        upgrade_database(app.config["DATABASE_URL"])

    @app.cli.command("db-stamp-head")
    def db_stamp_head() -> None:
        from .migrations import stamp_database

        stamp_database(app.config["DATABASE_URL"])
