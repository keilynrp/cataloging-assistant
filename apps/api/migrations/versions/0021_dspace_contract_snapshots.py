"""VERTICAL-022: canonical DSpace contract snapshots and changes.

Revision ID: 0021
Revises: 0020
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dspace_contract_snapshots",
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dspace_contract_sync_runs.run_id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("semantic_hash", sa.String(length=64), nullable=False),
        sa.Column("complete", sa.Boolean(), nullable=False),
        sa.Column("canonical_json", postgresql.JSONB(), nullable=False),
        sa.Column("warnings", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("run_id", name="uq_dspace_contract_snapshot_run"),
    )
    op.create_index("ix_dspace_contract_snapshots_run_id", "dspace_contract_snapshots", ["run_id"])
    op.create_index("ix_dspace_contract_snapshots_status", "dspace_contract_snapshots", ["status"])
    op.create_index(
        "ix_dspace_contract_snapshots_semantic_hash",
        "dspace_contract_snapshots",
        ["semantic_hash"],
    )
    op.create_index(
        "ix_dspace_contract_snapshots_status_created",
        "dspace_contract_snapshots",
        ["status", "created_at"],
    )

    op.create_table(
        "dspace_contract_changes",
        sa.Column("change_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dspace_contract_snapshots.snapshot_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("change_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("identity", sa.Text(), nullable=False),
        sa.Column("before_json", postgresql.JSONB(), nullable=True),
        sa.Column("after_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "detected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_dspace_contract_changes_snapshot_id", "dspace_contract_changes", ["snapshot_id"])
    op.create_index("ix_dspace_contract_changes_change_type", "dspace_contract_changes", ["change_type"])
    op.create_index("ix_dspace_contract_changes_severity", "dspace_contract_changes", ["severity"])
    op.create_index(
        "ix_dspace_contract_changes_snapshot_type",
        "dspace_contract_changes",
        ["snapshot_id", "change_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_dspace_contract_changes_snapshot_type", table_name="dspace_contract_changes")
    op.drop_index("ix_dspace_contract_changes_severity", table_name="dspace_contract_changes")
    op.drop_index("ix_dspace_contract_changes_change_type", table_name="dspace_contract_changes")
    op.drop_index("ix_dspace_contract_changes_snapshot_id", table_name="dspace_contract_changes")
    op.drop_table("dspace_contract_changes")

    op.drop_index("ix_dspace_contract_snapshots_status_created", table_name="dspace_contract_snapshots")
    op.drop_index("ix_dspace_contract_snapshots_semantic_hash", table_name="dspace_contract_snapshots")
    op.drop_index("ix_dspace_contract_snapshots_status", table_name="dspace_contract_snapshots")
    op.drop_index("ix_dspace_contract_snapshots_run_id", table_name="dspace_contract_snapshots")
    op.drop_table("dspace_contract_snapshots")
