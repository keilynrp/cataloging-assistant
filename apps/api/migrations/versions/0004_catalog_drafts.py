"""Versioned local catalog drafts.

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    draft_status = postgresql.ENUM("open", name="draft_status")
    draft_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "catalog_drafts",
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "item_uuid",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dspace_items.uuid"),
            nullable=False,
        ),
        sa.Column("base_source_hash", sa.String(64), nullable=False),
        sa.Column("base_metadata", postgresql.JSONB(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("open", name="draft_status", create_type=False),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("item_uuid", name="uq_catalog_drafts_item_uuid"),
    )
    op.create_index("ix_catalog_drafts_item_uuid", "catalog_drafts", ["item_uuid"])
    op.create_index("ix_catalog_drafts_base_source_hash", "catalog_drafts", ["base_source_hash"])
    op.create_index("ix_catalog_drafts_status", "catalog_drafts", ["status"])
    op.create_index("ix_catalog_drafts_updated_at", "catalog_drafts", ["updated_at"])
    op.create_index("ix_catalog_drafts_status_updated", "catalog_drafts", ["status", "updated_at"])

    op.create_table(
        "catalog_draft_revisions",
        sa.Column("revision_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column(
            "draft_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("catalog_drafts.draft_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("metadata_patch", postgresql.JSONB(), nullable=False),
        sa.Column("author", sa.String(120), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("draft_id", "version", name="uq_draft_revision_version"),
    )
    op.create_index("ix_catalog_draft_revisions_draft_id", "catalog_draft_revisions", ["draft_id"])
    op.create_index(
        "ix_catalog_draft_revisions_created_at", "catalog_draft_revisions", ["created_at"]
    )
    op.create_index(
        "ix_draft_revisions_draft_created",
        "catalog_draft_revisions",
        ["draft_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("catalog_draft_revisions")
    op.drop_table("catalog_drafts")
    postgresql.ENUM(name="draft_status").drop(op.get_bind(), checkfirst=True)
