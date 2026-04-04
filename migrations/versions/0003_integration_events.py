"""add integration event tracking

Revision ID: 0003_integration_events
Revises: 0002_add_users
Create Date: 2026-04-04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0003_integration_events"
down_revision = "0002_add_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("integration_events"):
        op.create_table(
            "integration_events",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("provider", sa.String(length=64), nullable=False),
            sa.Column("external_event_id", sa.String(length=255), nullable=True),
            sa.Column("dedupe_key", sa.String(length=255), nullable=False, unique=True),
            sa.Column("event_type", sa.String(length=128), nullable=True),
            sa.Column("signature", sa.String(length=255), nullable=True),
            sa.Column("timestamp_header", sa.String(length=64), nullable=True),
            sa.Column("payload_hash", sa.String(length=64), nullable=False),
            sa.Column("raw_body", sa.Text(), nullable=False),
            sa.Column("headers_json", sa.Text(), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=True),
            sa.Column(
                "status",
                sa.String(length=32),
                nullable=False,
                server_default=sa.text("'accepted'"),
            ),
            sa.Column("failure_reason", sa.Text(), nullable=True),
            sa.Column(
                "received_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
                sa.Column("processed_at", sa.DateTime(), nullable=True),
                sa.Column("dead_lettered_at", sa.DateTime(), nullable=True),
            )

    index_specs = {
        "ix_integration_events_provider": ["provider"],
        "ix_integration_events_external_event_id": ["external_event_id"],
        "ix_integration_events_event_type": ["event_type"],
        "ix_integration_events_payload_hash": ["payload_hash"],
        "ix_integration_events_received_at": ["received_at"],
    }
    existing_indexes = set()
    if inspector.has_table("integration_events"):
        existing_indexes = {index["name"] for index in inspector.get_indexes("integration_events")}

    for index_name, columns in index_specs.items():
        if index_name not in existing_indexes:
            op.create_index(index_name, "integration_events", columns, unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("integration_events"):
        existing_indexes = {index["name"] for index in inspector.get_indexes("integration_events")}
        for index_name in [
            "ix_integration_events_received_at",
            "ix_integration_events_payload_hash",
            "ix_integration_events_event_type",
            "ix_integration_events_external_event_id",
            "ix_integration_events_provider",
        ]:
            if index_name in existing_indexes:
                op.drop_index(index_name, table_name="integration_events")
        op.drop_table("integration_events")
