from __future__ import annotations

import uuid

from flask import Blueprint, redirect, render_template, request, url_for
from sqlalchemy import func, select

from ..auth import current_user, login_user, logout_user, sanitize_next_url
from ..db import session_scope
from ..models import User


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user() is not None:
        return redirect(url_for("web.dashboard"))

    error = None
    next_url = sanitize_next_url(
        request.args.get("next") or request.form.get("next") or url_for("web.dashboard")
    )

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        with session_scope() as db_session:
            user = db_session.scalar(select(User).where(User.email == email))

            if not user or not user.check_password(password) or not user.is_active:
                error = "Invalid email or password."
            else:
                login_user(user)
                return redirect(next_url)

    return render_template("login.html", error=error, next_url=next_url)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user() is not None:
        return redirect(url_for("web.dashboard"))

    error = None
    with session_scope() as db_session:
        user_count = db_session.scalar(select(func.count()).select_from(User)) or 0

    if user_count > 0:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if len(password) < 12:
            error = "Password must be at least 12 characters."
        elif password != confirm_password:
            error = "Passwords do not match."
        else:
            user = User(id=str(uuid.uuid4()), email=email, role="admin")
            user.set_password(password)

            with session_scope() as db_session:
                db_session.add(user)

            login_user(user)
            return redirect(url_for("web.dashboard"))

    return render_template("register.html", error=error)
