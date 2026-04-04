from __future__ import annotations

import uuid
from functools import wraps
from secrets import token_urlsafe
from urllib.parse import urlsplit

import click
from flask import g, jsonify, redirect, request, session, url_for
from sqlalchemy import func, select

from .db import session_scope
from .models import User
from .validation import ValidationError


USER_SESSION_KEY = "user_id"
CSRF_SESSION_KEY = "csrf_token"
ROLE_ADMIN = "admin"
ROLE_PROGRAM_OWNER = "program_owner"
ROLE_TRIAGER = "triager"
ROLE_RESEARCHER = "researcher"

ROLE_HIERARCHY = {
    ROLE_RESEARCHER: 10,
    ROLE_TRIAGER: 20,
    ROLE_PROGRAM_OWNER: 30,
    ROLE_ADMIN: 40,
}


def current_user():
    return getattr(g, "current_user", None)


def has_role(*roles: str) -> bool:
    user = current_user()
    return bool(user and user.role in roles)


def login_user(user: User) -> None:
    session.clear()
    session.permanent = True
    session[USER_SESSION_KEY] = user.id


def logout_user() -> None:
    session.clear()


def get_csrf_token() -> str:
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf_token(submitted_token: str | None) -> None:
    expected_token = session.get(CSRF_SESSION_KEY)
    if not expected_token or not submitted_token or submitted_token != expected_token:
        raise ValidationError("CSRF token is missing or invalid.")


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if current_user() is None:
            return redirect(url_for("auth.login", next=request.url))
        return view_func(*args, **kwargs)

    return wrapped_view


def role_required(*roles: str, api: bool = False):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            user = current_user()
            if user is None:
                if api:
                    return jsonify({"error": "Unauthorized", "status": 401}), 401
                return redirect(url_for("auth.login", next=request.url))

            if user.role not in roles:
                if api:
                    return jsonify({"error": "Forbidden", "status": 403}), 403
                return redirect(url_for("web.dashboard"))

            return view_func(*args, **kwargs)

        return wrapped_view

    return decorator


def sanitize_next_url(target: str | None) -> str:
    if not target:
        return url_for("web.dashboard")

    parts = urlsplit(target)
    if parts.scheme or parts.netloc:
        return url_for("web.dashboard")

    return target


def register_auth(app) -> None:
    @app.before_request
    def load_current_user() -> None:
        g.current_user = None
        user_id = session.get(USER_SESSION_KEY)
        if not user_id:
            return

        with session_scope() as db_session:
            user = db_session.get(User, user_id)
            if user and user.is_active:
                g.current_user = user
                session.permanent = True
                return

        session.clear()

    @app.before_request
    def enforce_csrf() -> None:
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return

        if request.path.startswith("/api/") or request.path.startswith("/webhook/"):
            return

        validate_csrf_token(request.form.get("csrf_token"))

    @app.context_processor
    def inject_auth_context():
        with session_scope() as db_session:
            user_count = db_session.scalar(select(func.count()).select_from(User)) or 0
        return {
            "current_user": current_user(),
            "has_role": has_role,
            "csrf_token": get_csrf_token,
            "bootstrap_registration_open": user_count == 0,
        }

    register_auth_commands(app)


def register_auth_commands(app) -> None:
    @app.cli.command("create-user")
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    @click.option(
        "--role",
        default="researcher",
        type=click.Choice(
            [ROLE_ADMIN, ROLE_PROGRAM_OWNER, ROLE_TRIAGER, ROLE_RESEARCHER]
        ),
        show_default=True,
    )
    def create_user_command(email: str, password: str, role: str) -> None:
        with session_scope() as db_session:
            existing = db_session.scalar(select(User).where(User.email == email.lower()))
            if existing:
                raise click.ClickException(f"User already exists for {email}")

            user = User(id=str(uuid.uuid4()), email=email.lower(), role=role)
            user.set_password(password)
            db_session.add(user)

        click.echo(f"Created user {email} with role {role}")
