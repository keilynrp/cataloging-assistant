"""Add restricted item provenance actors.

Revision ID: 0011
Revises: 0010_dspace_vocabularies
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011"
down_revision = "0010_dspace_vocabularies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dspace_item_provenance_actors",
        sa.Column("association_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "item_uuid",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dspace_items.uuid", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actor_key", sa.String(64), nullable=False),
        sa.Column("actor_type", sa.String(40), nullable=False),
        sa.Column("source_field", sa.String(255), nullable=False),
        sa.Column("source_position", sa.Integer(), nullable=False),
        sa.Column("source_text_hash", sa.String(64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("raw_evidence", postgresql.JSONB(), nullable=False),
        sa.Column(
            "synced_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "item_uuid",
            "source_field",
            "source_position",
            "actor_key",
            name="uq_item_provenance_actor_source",
        ),
    )
    op.create_index("ix_item_provenance_actor_item", "dspace_item_provenance_actors", ["item_uuid"])
    op.create_index("ix_item_provenance_actor_key", "dspace_item_provenance_actors", ["actor_key"])


def downgrade() -> None:
    op.drop_table("dspace_item_provenance_actors")
