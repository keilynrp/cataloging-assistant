"""Add read-only DSpace vocabulary mirror.

Revision ID: 0010_dspace_vocabularies
Revises: 0009_suggestion_decision_draft_revision
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_dspace_vocabularies"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dspace_vocabularies",
        sa.Column("vocabulary_id", sa.String(255), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("hierarchical", sa.Boolean(), nullable=False),
        sa.Column("scrollable", sa.Boolean(), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=False),
        sa.Column("raw_json", postgresql.JSONB(), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column(
            "synced_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "dspace_vocabulary_entries",
        sa.Column("row_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "vocabulary_id",
            sa.String(255),
            sa.ForeignKey("dspace_vocabularies.vocabulary_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entry_id", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("display", sa.Text()),
        sa.Column("selectable", sa.Boolean(), nullable=False),
        sa.Column("parent_id", sa.Text()),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("raw_json", postgresql.JSONB(), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column(
            "synced_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("vocabulary_id", "entry_id", name="uq_dspace_vocabulary_entry"),
    )
    op.create_index(
        "ix_dspace_vocabulary_entries_vocabulary_id", "dspace_vocabulary_entries", ["vocabulary_id"]
    )
    op.create_index(
        "ix_dspace_vocabulary_entries_value",
        "dspace_vocabulary_entries",
        ["vocabulary_id", "value"],
    )


def downgrade() -> None:
    op.drop_table("dspace_vocabulary_entries")
    op.drop_table("dspace_vocabularies")
