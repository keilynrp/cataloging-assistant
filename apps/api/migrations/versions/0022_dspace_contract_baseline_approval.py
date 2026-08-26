"""VERTICAL-022: governed DSpace contract baseline approval.

Revision ID: 0022
Revises: 0021
"""

import sqlalchemy as sa
from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dspace_contract_snapshots",
        sa.Column("approved_by", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "dspace_contract_snapshots",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "dspace_contract_snapshots",
        sa.Column("approval_note", sa.Text(), nullable=True),
    )
    op.add_column(
        "dspace_contract_snapshots",
        sa.Column("approved_hash", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "uq_dspace_contract_single_active",
        "dspace_contract_snapshots",
        ["status"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_dspace_contract_single_active",
        table_name="dspace_contract_snapshots",
    )
    op.drop_column("dspace_contract_snapshots", "approved_hash")
    op.drop_column("dspace_contract_snapshots", "approval_note")
    op.drop_column("dspace_contract_snapshots", "approved_at")
    op.drop_column("dspace_contract_snapshots", "approved_by")
