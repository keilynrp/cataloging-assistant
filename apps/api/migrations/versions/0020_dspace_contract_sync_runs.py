"""VERTICAL-022: DSpace contract sync runs and raw pages.

Revision ID: 0020
Revises: 0019
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dspace_contract_sync_runs",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("collector_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_surface", sa.String(length=80), nullable=True),
        sa.Column(
            "checkpoints",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("pages_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "raw_payload_hashes",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_dspace_contract_sync_runs_collector_version",
        "dspace_contract_sync_runs",
        ["collector_version"],
    )
    op.create_index(
        "ix_dspace_contract_sync_runs_status", "dspace_contract_sync_runs", ["status"]
    )
    op.create_index(
        "ix_dspace_contract_sync_runs_started_at",
        "dspace_contract_sync_runs",
        ["started_at"],
    )

    op.create_table(
        "dspace_contract_raw_pages",
        sa.Column("page_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dspace_contract_sync_runs.run_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("surface", sa.String(length=80), nullable=False),
        sa.Column("endpoint", sa.String(length=255), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column(
            "request_params",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("raw_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "captured_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "run_id", "surface", "page_number", name="uq_dspace_contract_raw_page"
        ),
    )
    op.create_index(
        "ix_dspace_contract_raw_pages_run_id", "dspace_contract_raw_pages", ["run_id"]
    )
    op.create_index(
        "ix_dspace_contract_raw_pages_raw_hash", "dspace_contract_raw_pages", ["raw_hash"]
    )
    op.create_index(
        "ix_dspace_contract_raw_pages_run_surface",
        "dspace_contract_raw_pages",
        ["run_id", "surface"],
    )


def downgrade() -> None:
    op.drop_index("ix_dspace_contract_raw_pages_run_surface", table_name="dspace_contract_raw_pages")
    op.drop_index("ix_dspace_contract_raw_pages_raw_hash", table_name="dspace_contract_raw_pages")
    op.drop_index("ix_dspace_contract_raw_pages_run_id", table_name="dspace_contract_raw_pages")
    op.drop_table("dspace_contract_raw_pages")

    op.drop_index("ix_dspace_contract_sync_runs_started_at", table_name="dspace_contract_sync_runs")
    op.drop_index("ix_dspace_contract_sync_runs_status", table_name="dspace_contract_sync_runs")
    op.drop_index(
        "ix_dspace_contract_sync_runs_collector_version", table_name="dspace_contract_sync_runs"
    )
    op.drop_table("dspace_contract_sync_runs")
