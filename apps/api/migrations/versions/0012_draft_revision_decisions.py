"""Add auditable decisions for draft revisions.

Revision ID: 0012
Revises: 0011
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    decision_kind = postgresql.ENUM(
        "approved",
        "rejected",
        name="draft_revision_decision_kind",
        create_type=False,
    )
    postgresql.ENUM(
        "approved",
        "rejected",
        name="draft_revision_decision_kind",
    ).create(op.get_bind(), checkfirst=True)
    op.create_table(
        "catalog_draft_revision_decisions",
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", decision_kind, nullable=False),
        sa.Column("reviewer", sa.String(length=120), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("validation_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("validation_override", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["draft_id"], ["catalog_drafts.draft_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["revision_id"], ["catalog_draft_revisions.revision_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["item_uuid"], ["dspace_items.uuid"]),
    )
    op.create_index(
        "ix_draft_revision_decisions_revision_created",
        "catalog_draft_revision_decisions",
        ["revision_id", "created_at"],
    )
    op.create_index(
        "ix_draft_revision_decisions_item_created",
        "catalog_draft_revision_decisions",
        ["item_uuid", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("catalog_draft_revision_decisions")
    sa.Enum(name="draft_revision_decision_kind").drop(op.get_bind(), checkfirst=True)
