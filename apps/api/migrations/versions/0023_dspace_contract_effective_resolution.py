"""VERTICAL-022: authoritative evidence resolution for unobservable DSpace surfaces.

Revision ID: 0023
Revises: 0022
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dspace_contract_snapshots",
        sa.Column("effective_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "dspace_contract_snapshots",
        sa.Column("effective_canonical_json", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "dspace_contract_snapshots",
        sa.Column("resolution_surface", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "dspace_contract_snapshots",
        sa.Column("resolution_source_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "dspace_contract_snapshots",
        sa.Column("resolution_reconciliation_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "dspace_contract_snapshots",
        sa.Column("resolved_by", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "dspace_contract_snapshots",
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "dspace_contract_snapshots",
        sa.Column("resolution_note", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_dspace_contract_snapshots_effective_hash",
        "dspace_contract_snapshots",
        ["effective_hash"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_dspace_contract_snapshots_effective_hash",
        table_name="dspace_contract_snapshots",
    )
    op.drop_column("dspace_contract_snapshots", "resolution_note")
    op.drop_column("dspace_contract_snapshots", "resolved_at")
    op.drop_column("dspace_contract_snapshots", "resolved_by")
    op.drop_column("dspace_contract_snapshots", "resolution_reconciliation_hash")
    op.drop_column("dspace_contract_snapshots", "resolution_source_hash")
    op.drop_column("dspace_contract_snapshots", "resolution_surface")
    op.drop_column("dspace_contract_snapshots", "effective_canonical_json")
    op.drop_column("dspace_contract_snapshots", "effective_hash")
