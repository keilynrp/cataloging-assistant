"""VERTICAL-019: PDF evidence sources.

Revision ID: 0019
Revises: 0018
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "catalog_evidence_sources",
        sa.Column(
            "extraction_status",
            sa.String(length=30),
            nullable=False,
            server_default="extracted",
        ),
    )
    op.add_column(
        "catalog_evidence_sources",
        sa.Column(
            "extraction_metadata_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "catalog_evidence_sources",
        sa.Column("extracted_text_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "catalog_evidence_sources",
        sa.Column("page_count", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("catalog_evidence_sources", "page_count")
    op.drop_column("catalog_evidence_sources", "extracted_text_hash")
    op.drop_column("catalog_evidence_sources", "extraction_metadata_json")
    op.drop_column("catalog_evidence_sources", "extraction_status")
