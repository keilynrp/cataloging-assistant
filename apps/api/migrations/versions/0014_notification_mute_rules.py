"""Simple per-event-type mute preferences for the pilot recipient.

Revision ID: 0014
Revises: 0013
"""

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_mute_rules",
        sa.Column("event_type", sa.String(100), primary_key=True),
        sa.Column("muted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("muted_by", sa.String(120), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("notification_mute_rules")
