"""VERTICAL-017: controlled external evidence sessions.

Revision ID: 0018
Revises: 0017
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalog_evidence_sessions",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "item_uuid",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dspace_items.uuid", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("base_source_hash", sa.String(length=64), nullable=True),
        sa.Column("contract_version", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_catalog_evidence_sessions_item_uuid",
        "catalog_evidence_sessions",
        ["item_uuid"],
    )
    op.create_index(
        "ix_catalog_evidence_sessions_base_source_hash",
        "catalog_evidence_sessions",
        ["base_source_hash"],
    )

    op.create_table(
        "catalog_evidence_sources",
        sa.Column("source_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("catalog_evidence_sessions.session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("locator", sa.Text(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("media_type", sa.String(length=255), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_catalog_evidence_sources_session_id",
        "catalog_evidence_sources",
        ["session_id"],
    )
    op.create_index(
        "ix_catalog_evidence_sources_content_hash",
        "catalog_evidence_sources",
        ["content_hash"],
    )
    op.create_index(
        "ix_evidence_sources_session_created",
        "catalog_evidence_sources",
        ["session_id", "created_at"],
    )

    op.create_table(
        "catalog_evidence_candidates",
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("catalog_evidence_sessions.session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("catalog_evidence_sources.source_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("binding_id", sa.String(length=120), nullable=False),
        sa.Column("metadata_field", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("evidence_state", sa.String(length=30), nullable=False),
        sa.Column("evidence_json", postgresql.JSONB(), nullable=False),
        sa.Column(
            "validation_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    for column in (
        "session_id",
        "source_id",
        "binding_id",
        "metadata_field",
        "evidence_state",
    ):
        op.create_index(
            f"ix_catalog_evidence_candidates_{column}",
            "catalog_evidence_candidates",
            [column],
        )
    op.create_index(
        "ix_evidence_candidates_session_field",
        "catalog_evidence_candidates",
        ["session_id", "metadata_field"],
    )


def downgrade() -> None:
    op.drop_table("catalog_evidence_candidates")
    op.drop_table("catalog_evidence_sources")
    op.drop_table("catalog_evidence_sessions")
