"""Approved controlled vocabulary revisions.

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalog_vocabulary_revisions",
        sa.Column("revision_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("field", sa.String(255), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=False),
        sa.Column("version_label", sa.String(120), nullable=False),
        sa.Column("approved_by", sa.String(120), nullable=False),
        sa.Column("approval_note", sa.Text(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_catalog_vocabulary_revisions_field",
        "catalog_vocabulary_revisions",
        ["field"],
    )
    op.create_index(
        "ix_catalog_vocabulary_revisions_active_created",
        "catalog_vocabulary_revisions",
        ["is_active", "created_at"],
    )
    op.create_index(
        "uq_catalog_vocabulary_active_field",
        "catalog_vocabulary_revisions",
        ["field"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    op.create_table(
        "catalog_controlled_terms",
        sa.Column("term_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "revision_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("catalog_vocabulary_revisions.revision_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("normalized_value", sa.Text(), nullable=False),
        sa.Column("authority", sa.Text(), nullable=True),
        sa.Column("language", sa.String(64), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "revision_id",
            "normalized_value",
            name="uq_catalog_term_revision_normalized",
        ),
        sa.UniqueConstraint(
            "revision_id",
            "position",
            name="uq_catalog_term_revision_position",
        ),
    )
    op.create_index(
        "ix_catalog_controlled_terms_revision_id",
        "catalog_controlled_terms",
        ["revision_id"],
    )
    op.create_index(
        "ix_catalog_controlled_terms_normalized",
        "catalog_controlled_terms",
        ["normalized_value"],
    )


def downgrade() -> None:
    op.drop_table("catalog_controlled_terms")
    op.drop_table("catalog_vocabulary_revisions")
