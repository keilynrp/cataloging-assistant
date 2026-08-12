"""Versioned cataloguing diagnostics.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("dspace_items", sa.Column("diagnostic_source_hash", sa.String(64)))
    op.add_column("dspace_items", sa.Column("diagnostic_profile_version", sa.String(64)))
    op.add_column("dspace_items", sa.Column("diagnosed_at", sa.DateTime(timezone=True)))

    op.create_table(
        "catalog_findings",
        sa.Column(
            "finding_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "item_uuid",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dspace_items.uuid", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(30), nullable=False),
        sa.Column("affected_fields", postgresql.JSONB(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("rule_version", sa.String(64), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("item_uuid", "fingerprint", name="uq_finding_item_fingerprint"),
    )
    op.create_index("ix_catalog_findings_item_uuid", "catalog_findings", ["item_uuid"])
    op.create_index("ix_catalog_findings_code", "catalog_findings", ["code"])
    op.create_index("ix_catalog_findings_severity", "catalog_findings", ["severity"])
    op.create_index("ix_catalog_findings_code_severity", "catalog_findings", ["code", "severity"])


def downgrade() -> None:
    op.drop_table("catalog_findings")
    op.drop_column("dspace_items", "diagnosed_at")
    op.drop_column("dspace_items", "diagnostic_profile_version")
    op.drop_column("dspace_items", "diagnostic_source_hash")
