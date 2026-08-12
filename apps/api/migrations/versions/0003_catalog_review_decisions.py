"""Append-only catalog review decisions.

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    decision_kind = postgresql.ENUM(
        "confirmed", "dismissed", "deferred", name="review_decision_kind"
    )
    decision_kind.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "catalog_review_decisions",
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column(
            "item_uuid",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dspace_items.uuid"),
            nullable=False,
        ),
        sa.Column("finding_fingerprint", sa.String(64), nullable=False),
        sa.Column("finding_code", sa.String(100), nullable=False),
        sa.Column("finding_severity", sa.String(30), nullable=False),
        sa.Column("finding_affected_fields", postgresql.JSONB(), nullable=False),
        sa.Column("finding_explanation", sa.Text(), nullable=False),
        sa.Column("finding_rule_version", sa.String(64), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column(
            "decision",
            postgresql.ENUM(
                "confirmed",
                "dismissed",
                "deferred",
                name="review_decision_kind",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("reviewer", sa.String(120), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_catalog_review_decisions_request_id",
        "catalog_review_decisions",
        ["request_id"],
        unique=True,
    )
    op.create_index(
        "ix_catalog_review_decisions_item_uuid", "catalog_review_decisions", ["item_uuid"]
    )
    op.create_index(
        "ix_catalog_review_decisions_finding_code", "catalog_review_decisions", ["finding_code"]
    )
    op.create_index(
        "ix_catalog_review_decisions_decision", "catalog_review_decisions", ["decision"]
    )
    op.create_index(
        "ix_catalog_review_decisions_created_at", "catalog_review_decisions", ["created_at"]
    )
    op.create_index(
        "ix_review_decisions_item_created",
        "catalog_review_decisions",
        ["item_uuid", "created_at"],
    )
    op.create_index(
        "ix_review_decisions_fingerprint",
        "catalog_review_decisions",
        ["item_uuid", "finding_fingerprint"],
    )


def downgrade() -> None:
    op.drop_table("catalog_review_decisions")
    postgresql.ENUM(name="review_decision_kind").drop(op.get_bind(), checkfirst=True)
