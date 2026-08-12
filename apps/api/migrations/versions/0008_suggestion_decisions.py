"""Persist append-only suggestion decisions.

Revision ID: 0008
Revises: 0007
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    kind = postgresql.ENUM(
        "accepted", "corrected", "rejected", "deferred", name="suggestion_decision_kind"
    )
    kind.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "catalog_suggestion_decisions",
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column(
            "suggestion_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("catalog_suggestions.suggestion_id"),
            nullable=False,
        ),
        sa.Column(
            "item_uuid",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dspace_items.uuid"),
            nullable=False,
        ),
        sa.Column(
            "decision",
            postgresql.ENUM(name="suggestion_decision_kind", create_type=False),
            nullable=False,
        ),
        sa.Column("corrected_value", sa.Text()),
        sa.Column("reviewer", sa.String(120), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("suggestion_source_hash", sa.String(64), nullable=False),
        sa.Column("current_source_hash", sa.String(64), nullable=False),
        sa.Column("source_stale", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_suggestion_decisions_suggestion_created",
        "catalog_suggestion_decisions",
        ["suggestion_id", "created_at"],
    )
    op.create_index(
        "ix_catalog_suggestion_decisions_item_uuid", "catalog_suggestion_decisions", ["item_uuid"]
    )


def downgrade() -> None:
    op.drop_table("catalog_suggestion_decisions")
    postgresql.ENUM(name="suggestion_decision_kind").drop(op.get_bind(), checkfirst=True)
