"""Append-only conversations and messages for the conversational agent.

Revision ID: 0015
Revises: 0014
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conversation_status = postgresql.ENUM(
        "open", "archived", name="agent_conversation_status"
    )
    conversation_status.create(op.get_bind(), checkfirst=True)
    message_role = postgresql.ENUM("user", "assistant", name="agent_message_role")
    message_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "agent_conversations",
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("collection_uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_by", sa.String(120), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "open", "archived", name="agent_conversation_status", create_type=False
            ),
            nullable=False,
            server_default="open",
        ),
    )
    op.create_index(
        "ix_agent_conversations_collection_uuid", "agent_conversations", ["collection_uuid"]
    )
    op.create_index("ix_agent_conversations_status", "agent_conversations", ["status"])

    op.create_table(
        "agent_messages",
        sa.Column("message_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_conversations.conversation_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            postgresql.ENUM("user", "assistant", name="agent_message_role", create_type=False),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_calls", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("citations", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("model", sa.String(64), nullable=True),
        sa.Column("usage", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_agent_messages_conversation_id", "agent_messages", ["conversation_id"])
    op.create_index("ix_agent_messages_role", "agent_messages", ["role"])
    op.create_index("ix_agent_messages_created_at", "agent_messages", ["created_at"])
    op.create_index(
        "ix_agent_messages_conversation_created",
        "agent_messages",
        ["conversation_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("agent_messages")
    op.drop_table("agent_conversations")
    postgresql.ENUM(name="agent_message_role").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="agent_conversation_status").drop(op.get_bind(), checkfirst=True)
