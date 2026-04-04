from __future__ import annotations

import uuid

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..auth import (
    ROLE_ADMIN,
    ROLE_PROGRAM_OWNER,
    ROLE_RESEARCHER,
    ROLE_TRIAGER,
    current_user,
    login_required,
    role_required,
)
from ..db import session_scope
from ..models import Program, Researcher, Submission
from ..validation import optional_money, optional_text, require_choice, require_text


SEVERITY_CHOICES = {"low", "medium", "high", "critical"}
SUBMISSION_STATUS_CHOICES = {"submitted", "triaged", "in_progress", "resolved", "closed"}


web_bp = Blueprint("web", __name__)


@web_bp.route("/")
def index():
    return render_template("index.html")


@web_bp.route("/dashboard")
@login_required
def dashboard():
    with session_scope() as session:
        programs_count = session.scalar(select(func.count()).select_from(Program)) or 0
        submissions_count = (
            session.scalar(select(func.count()).select_from(Submission)) or 0
        )
        resolved_count = (
            session.scalar(
                select(func.count())
                .select_from(Submission)
                .where(Submission.status == "resolved")
            )
            or 0
        )
        total_paid = session.scalar(select(func.sum(Submission.bounty))) or 0
        recent = session.scalars(
            select(Submission)
            .options(selectinload(Submission.program))
            .order_by(Submission.created_at.desc())
            .limit(10)
        ).all()

    return render_template(
        "dashboard.html",
        programs_count=programs_count,
        submissions_count=submissions_count,
        resolved_count=resolved_count,
        total_paid=total_paid,
        recent=recent,
    )


@web_bp.route("/programs")
@role_required(ROLE_ADMIN, ROLE_PROGRAM_OWNER, ROLE_TRIAGER, ROLE_RESEARCHER)
def programs():
    with session_scope() as session:
        programs = session.scalars(
            select(Program).order_by(Program.created_at.desc())
        ).all()

    return render_template("programs.html", programs=programs)


@web_bp.route("/programs/new", methods=["GET", "POST"])
@role_required(ROLE_ADMIN, ROLE_PROGRAM_OWNER)
def new_program():
    if request.method == "POST":
        program = Program(
            id=str(uuid.uuid4()),
            name=require_text(request.form, "name", label="Name"),
            description=optional_text(request.form, "description"),
            scope=optional_text(request.form, "scope"),
            rules=optional_text(request.form, "rules"),
            bounty_range=optional_text(request.form, "bounty_range") or "",
        )

        with session_scope() as session:
            session.add(program)

        return redirect(url_for("web.programs"))

    return render_template("program_form.html", program=None)


@web_bp.route("/programs/<program_id>")
@role_required(ROLE_ADMIN, ROLE_PROGRAM_OWNER, ROLE_TRIAGER, ROLE_RESEARCHER)
def program_detail(program_id):
    with session_scope() as session:
        program = session.get(Program, program_id)
        if not program:
            abort(404)

        submissions = session.scalars(
            select(Submission)
            .where(Submission.program_id == program_id)
            .order_by(Submission.created_at.desc())
        ).all()

    return render_template("program_detail.html", program=program, submissions=submissions)


@web_bp.route("/submissions")
@role_required(ROLE_ADMIN, ROLE_PROGRAM_OWNER, ROLE_TRIAGER)
def submissions():
    with session_scope() as session:
        submissions = session.scalars(
            select(Submission)
            .options(selectinload(Submission.program))
            .order_by(Submission.created_at.desc())
        ).all()

    return render_template("submissions.html", submissions=submissions)


@web_bp.route("/submissions/new", methods=["GET", "POST"])
@role_required(ROLE_ADMIN, ROLE_PROGRAM_OWNER, ROLE_TRIAGER, ROLE_RESEARCHER)
def new_submission():
    if request.method == "POST":
        submission = Submission(
            id=str(uuid.uuid4()),
            program_id=optional_text(request.form, "program_id"),
            researcher=require_text(request.form, "researcher", label="Researcher name"),
            title=require_text(request.form, "title", label="Vulnerability title"),
            description=require_text(request.form, "description", label="Description"),
            severity=require_choice(
                request.form,
                "severity",
                SEVERITY_CHOICES,
                label="Severity",
            ),
        )

        with session_scope() as session:
            session.add(submission)

        return redirect(url_for("web.submissions"))

    with session_scope() as session:
        programs = session.scalars(select(Program).order_by(Program.name.asc())).all()

    return render_template("submission_form.html", programs=programs)


@web_bp.route("/submissions/<submission_id>", methods=["GET", "POST"])
@login_required
def submission_detail(submission_id):
    required_roles = (
        {ROLE_ADMIN, ROLE_PROGRAM_OWNER, ROLE_TRIAGER}
        if request.method == "POST"
        else {ROLE_ADMIN, ROLE_PROGRAM_OWNER, ROLE_TRIAGER, ROLE_RESEARCHER}
    )

    with session_scope() as session:
        submission = session.scalar(
            select(Submission)
            .options(selectinload(Submission.program))
            .where(Submission.id == submission_id)
        )

        if not submission:
            abort(404)

        if current_user().role not in required_roles:
            return redirect(url_for("web.dashboard"))

        if request.method == "POST":
            submission.status = require_choice(
                request.form,
                "status",
                SUBMISSION_STATUS_CHOICES,
                label="Status",
            )
            submission.severity = require_choice(
                request.form,
                "severity",
                SEVERITY_CHOICES,
                label="Severity",
            )
            submission.bounty = optional_money(request.form, "bounty")

    return render_template("submission_detail.html", submission=submission)


@web_bp.route("/researchers")
@role_required(ROLE_ADMIN, ROLE_TRIAGER)
def researchers():
    with session_scope() as session:
        researchers = session.scalars(
            select(Researcher).order_by(Researcher.reputation.desc())
        ).all()

    return render_template("researchers.html", researchers=researchers)


@web_bp.route("/health")
def health():
    return jsonify(
        {
            "status": "healthy",
            "version": "1.0.0",
            "features": [
                "Program Management",
                "Submission Tracking",
                "Researcher Portal",
                "API Access",
                "Webhook Integration",
            ],
        }
    )
