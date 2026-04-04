from __future__ import annotations

import uuid

from flask import Blueprint, jsonify, request
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..auth import (
    ROLE_ADMIN,
    ROLE_PROGRAM_OWNER,
    ROLE_RESEARCHER,
    ROLE_TRIAGER,
    role_required,
)
from ..db import session_scope
from ..models import Program, Submission
from ..validation import optional_text, require_choice, require_json_body, require_text


SEVERITY_CHOICES = {"low", "medium", "high", "critical"}


api_bp = Blueprint("api", __name__)


@api_bp.route("/programs", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_PROGRAM_OWNER, ROLE_TRIAGER, ROLE_RESEARCHER, api=True)
def api_programs():
    with session_scope() as session:
        programs = session.scalars(
            select(Program).order_by(Program.created_at.desc())
        ).all()

    return jsonify([program.to_dict() for program in programs])


@api_bp.route("/programs", methods=["POST"])
@role_required(ROLE_ADMIN, ROLE_PROGRAM_OWNER, api=True)
def api_create_program():
    data = require_json_body(request.get_json(silent=True))
    program = Program(
        id=str(uuid.uuid4()),
        name=require_text(data, "name", label="name"),
        description=optional_text(data, "description"),
        scope=optional_text(data, "scope"),
        rules=optional_text(data, "rules"),
        bounty_range=optional_text(data, "bounty_range"),
    )

    with session_scope() as session:
        session.add(program)

    return jsonify({"id": program.id, "success": True})


@api_bp.route("/submissions", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_PROGRAM_OWNER, ROLE_TRIAGER, api=True)
def api_submissions():
    with session_scope() as session:
        submissions = session.scalars(
            select(Submission)
            .options(selectinload(Submission.program))
            .order_by(Submission.created_at.desc())
        ).all()

    return jsonify([submission.to_dict() for submission in submissions])


@api_bp.route("/submissions", methods=["POST"])
@role_required(ROLE_ADMIN, ROLE_PROGRAM_OWNER, ROLE_TRIAGER, ROLE_RESEARCHER, api=True)
def api_create_submission():
    data = require_json_body(request.get_json(silent=True))
    submission = Submission(
        id=str(uuid.uuid4()),
        program_id=optional_text(data, "program_id"),
        researcher=require_text(data, "researcher", label="researcher"),
        title=require_text(data, "title", label="title"),
        description=require_text(data, "description", label="description"),
        severity=require_choice(data, "severity", SEVERITY_CHOICES, label="severity"),
    )

    with session_scope() as session:
        session.add(submission)

    return jsonify({"id": submission.id, "success": True})


@api_bp.route("/stats")
@role_required(ROLE_ADMIN, ROLE_PROGRAM_OWNER, ROLE_TRIAGER, api=True)
def api_stats():
    with session_scope() as session:
        programs = session.scalar(select(func.count()).select_from(Program)) or 0
        submissions = (
            session.scalar(select(func.count()).select_from(Submission)) or 0
        )
        resolved = (
            session.scalar(
                select(func.count())
                .select_from(Submission)
                .where(Submission.status == "resolved")
            )
            or 0
        )
        total_paid = session.scalar(select(func.sum(Submission.bounty))) or 0

    return jsonify(
        {
            "programs": programs,
            "submissions": submissions,
            "resolved": resolved,
            "total_paid": total_paid,
        }
    )
