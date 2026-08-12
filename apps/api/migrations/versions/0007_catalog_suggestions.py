"""Persist immutable catalog suggestions.

Revision ID: 0007
Revises: 0006
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalog_suggestions",
        sa.Column("suggestion_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "item_uuid",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dspace_items.uuid"),
            nullable=False,
        ),
        sa.Column("fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("field", sa.String(255), nullable=False),
        sa.Column("proposed_value", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("method", sa.String(100), nullable=False),
        sa.Column("method_version", sa.String(64), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    for column in ("item_uuid", "fingerprint", "source_hash", "field", "created_at"):
        op.create_index(f"ix_catalog_suggestions_{column}", "catalog_suggestions", [column])
    op.create_index(
        "ix_catalog_suggestions_item_created", "catalog_suggestions", ["item_uuid", "created_at"]
    )


def downgrade() -> None:
    op.drop_table("catalog_suggestions")
