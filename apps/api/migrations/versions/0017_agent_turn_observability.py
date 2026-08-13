"""AGT-008: first-chunk latency on agent_messages and an append-only turn-error log.

Revision ID: 0017
Revises: 0016
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_messages", sa.Column("latency_ms", sa.Integer(), nullable=True))

    op.create_table(
        "agent_turn_errors",
        sa.Column("error_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_conversations.conversation_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_agent_turn_errors_conversation_id", "agent_turn_errors", ["conversation_id"])
    op.create_index("ix_agent_turn_errors_created_at", "agent_turn_errors", ["created_at"])
    op.create_index(
        "ix_agent_turn_errors_conversation_created",
        "agent_turn_errors",
        ["conversation_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("agent_turn_errors")
    op.drop_column("agent_messages", "latency_ms")
