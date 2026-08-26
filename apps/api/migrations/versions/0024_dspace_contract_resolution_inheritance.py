"""VERTICAL-022: track inherited authoritative resolution provenance.

Revision ID: 0024
Revises: 0023
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dspace_contract_snapshots",
        sa.Column(
            "resolution_inherited_from_snapshot_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_dspace_contract_resolution_inherited_from",
        "dspace_contract_snapshots",
        "dspace_contract_snapshots",
        ["resolution_inherited_from_snapshot_id"],
        ["snapshot_id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_dspace_contract_resolution_inherited_from",
        "dspace_contract_snapshots",
        ["resolution_inherited_from_snapshot_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_dspace_contract_resolution_inherited_from",
        table_name="dspace_contract_snapshots",
    )
    op.drop_constraint(
        "fk_dspace_contract_resolution_inherited_from",
        "dspace_contract_snapshots",
        type_="foreignkey",
    )
    op.drop_column(
        "dspace_contract_snapshots",
        "resolution_inherited_from_snapshot_id",
    )
