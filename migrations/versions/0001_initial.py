"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "programs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("rules", sa.Text(), nullable=True),
        sa.Column("bounty_range", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "researchers",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("username", sa.String(length=255), nullable=False, unique=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column(
            "reputation",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "bugs_found",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "total_earnings",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "settings",
        sa.Column("key", sa.String(length=255), primary_key=True),
        sa.Column("value", sa.Text(), nullable=True),
    )

    op.create_table(
        "submissions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "program_id",
            sa.String(length=36),
            sa.ForeignKey("programs.id"),
            nullable=True,
        ),
        sa.Column("researcher", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'submitted'"),
        ),
        sa.Column("bounty", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_index("ix_submissions_program_id", "submissions", ["program_id"])
    op.create_index("ix_submissions_severity", "submissions", ["severity"])
    op.create_index("ix_submissions_created_at", "submissions", ["created_at"])
    op.create_index("ix_researchers_reputation", "researchers", ["reputation"])


def downgrade() -> None:
    op.drop_index("ix_researchers_reputation", table_name="researchers")
    op.drop_index("ix_submissions_created_at", table_name="submissions")
    op.drop_index("ix_submissions_severity", table_name="submissions")
    op.drop_index("ix_submissions_program_id", table_name="submissions")
    op.drop_table("submissions")
    op.drop_table("settings")
    op.drop_table("researchers")
    op.drop_table("programs")

