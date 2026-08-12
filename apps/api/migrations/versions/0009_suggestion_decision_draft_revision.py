"""Link suggestion decisions to draft revisions.

Revision ID: 0009
Revises: 0008
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "catalog_suggestion_decisions",
        sa.Column("draft_revision_id", postgresql.UUID(as_uuid=True)),
    )
    op.create_foreign_key(
        "fk_suggestion_decision_draft_revision",
        "catalog_suggestion_decisions",
        "catalog_draft_revisions",
        ["draft_revision_id"],
        ["revision_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_suggestion_decision_draft_revision",
        "catalog_suggestion_decisions",
        type_="foreignkey",
    )
    op.drop_column("catalog_suggestion_decisions", "draft_revision_id")
