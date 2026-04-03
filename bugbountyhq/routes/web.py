from __future__ import annotations

import uuid

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..auth import login_required
from ..db import session_scope
from ..models import Program, Researcher, Submission


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
@login_required
def programs():
    with session_scope() as session:
        programs = session.scalars(
            select(Program).order_by(Program.created_at.desc())
        ).all()

    return render_template("programs.html", programs=programs)


@web_bp.route("/programs/new", methods=["GET", "POST"])
@login_required
def new_program():
    if request.method == "POST":
        data = request.form
        program = Program(
            id=str(uuid.uuid4()),
            name=data["name"],
            description=data["description"],
            scope=data["scope"],
            rules=data["rules"],
            bounty_range=data.get("bounty_range", ""),
        )

        with session_scope() as session:
            session.add(program)

        return redirect(url_for("web.programs"))

    return render_template("program_form.html", program=None)


@web_bp.route("/programs/<program_id>")
@login_required
def program_detail(program_id):
    with session_scope() as session:
        program = session.get(Program, program_id)
        if program:
            submissions = session.scalars(
                select(Submission)
                .where(Submission.program_id == program_id)
                .order_by(Submission.created_at.desc())
            ).all()
        else:
            submissions = []

    return render_template("program_detail.html", program=program, submissions=submissions)


@web_bp.route("/submissions")
@login_required
def submissions():
    with session_scope() as session:
        submissions = session.scalars(
            select(Submission)
            .options(selectinload(Submission.program))
            .order_by(Submission.created_at.desc())
        ).all()

    return render_template("submissions.html", submissions=submissions)


@web_bp.route("/submissions/new", methods=["GET", "POST"])
@login_required
def new_submission():
    if request.method == "POST":
        data = request.form
        submission = Submission(
            id=str(uuid.uuid4()),
            program_id=data.get("program_id") or None,
            researcher=data["researcher"],
            title=data["title"],
            description=data["description"],
            severity=data["severity"],
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
    with session_scope() as session:
        submission = session.scalar(
            select(Submission)
            .options(selectinload(Submission.program))
            .where(Submission.id == submission_id)
        )

        if request.method == "POST" and submission:
            data = request.form
            submission.status = data["status"]
            submission.severity = data["severity"]
            submission.bounty = float(data["bounty"]) if data["bounty"] else None

    return render_template("submission_detail.html", submission=submission)


@web_bp.route("/researchers")
@login_required
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
