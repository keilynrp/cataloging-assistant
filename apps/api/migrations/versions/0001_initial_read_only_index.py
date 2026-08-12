"""Initial read-only DSpace index.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dspace_collections",
        sa.Column("uuid", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("handle", sa.String(255)),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("last_modified", sa.DateTime(timezone=True)),
        sa.Column("raw_json", postgresql.JSONB(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_dspace_collections_handle", "dspace_collections", ["handle"])
    op.create_index("ix_dspace_collections_last_modified", "dspace_collections", ["last_modified"])

    op.create_table(
        "dspace_items",
        sa.Column("uuid", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "collection_uuid",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dspace_collections.uuid"),
            nullable=False,
        ),
        sa.Column("handle", sa.String(255)),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("last_modified", sa.DateTime(timezone=True)),
        sa.Column("raw_json", postgresql.JSONB(), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in (
        "collection_uuid",
        "handle",
        "name",
        "last_modified",
        "source_hash",
        "is_active",
    ):
        op.create_index(f"ix_dspace_items_{column}", "dspace_items", [column])

    op.create_table(
        "dspace_metadata",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "item_uuid",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dspace_items.uuid", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field", sa.String(255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("language", sa.String(64)),
        sa.Column("authority", sa.Text()),
        sa.Column("confidence", sa.Integer()),
        sa.Column("place", sa.Integer(), nullable=False),
        sa.UniqueConstraint("item_uuid", "field", "place", name="uq_metadata_item_field_place"),
    )
    op.create_index("ix_dspace_metadata_item_uuid", "dspace_metadata", ["item_uuid"])
    op.create_index("ix_dspace_metadata_field", "dspace_metadata", ["field"])
    op.create_index("ix_metadata_field_value", "dspace_metadata", ["field", "value"])

    op.create_table(
        "dspace_bundles",
        sa.Column("uuid", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "item_uuid",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dspace_items.uuid", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("raw_json", postgresql.JSONB(), nullable=False),
    )
    op.create_index("ix_dspace_bundles_item_uuid", "dspace_bundles", ["item_uuid"])
    op.create_index("ix_dspace_bundles_name", "dspace_bundles", ["name"])

    op.create_table(
        "dspace_bitstreams",
        sa.Column("uuid", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "bundle_uuid",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dspace_bundles.uuid", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(255)),
        sa.Column("size_bytes", sa.Integer()),
        sa.Column("content_url", sa.Text()),
        sa.Column("raw_json", postgresql.JSONB(), nullable=False),
    )
    op.create_index("ix_dspace_bitstreams_bundle_uuid", "dspace_bitstreams", ["bundle_uuid"])
    op.create_index("ix_dspace_bitstreams_mime_type", "dspace_bitstreams", ["mime_type"])

    sync_status = postgresql.ENUM(
        "queued", "running", "succeeded", "partial", "failed", name="sync_status"
    )
    sync_status.create(op.get_bind())
    sync_status_for_column = postgresql.ENUM(
        "queued", "running", "succeeded", "partial", "failed", name="sync_status", create_type=False
    )
    op.create_table(
        "sync_runs",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("collection_uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sync_status_for_column, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("checkpoint_page", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_changed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(100)),
        sa.Column("error_detail", sa.Text()),
        sa.Column(
            "metrics", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
    )
    op.create_index("ix_sync_runs_collection_uuid", "sync_runs", ["collection_uuid"])
    op.create_index("ix_sync_runs_status", "sync_runs", ["status"])


def downgrade() -> None:
    op.drop_table("sync_runs")
    postgresql.ENUM(name="sync_status").drop(op.get_bind())
    op.drop_table("dspace_bitstreams")
    op.drop_table("dspace_bundles")
    op.drop_table("dspace_metadata")
    op.drop_table("dspace_items")
    op.drop_table("dspace_collections")
