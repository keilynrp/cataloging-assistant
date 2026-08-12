"""Notification events, outbox and per-recipient deliveries.

Revision ID: 0013
Revises: 0012
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    severity = postgresql.ENUM("info", "warning", "error", name="notification_severity")
    severity.create(op.get_bind(), checkfirst=True)
    delivery_state = postgresql.ENUM(
        "unread", "read", "archived", name="notification_delivery_state"
    )
    delivery_state.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "notification_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("aggregate_type", sa.String(50), nullable=False),
        sa.Column("aggregate_id", sa.String(255), nullable=False),
        sa.Column("collection_uuid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "severity",
            postgresql.ENUM("info", "warning", "error", name="notification_severity", create_type=False),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("target_path", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("deduplication_key", sa.String(255), nullable=False, unique=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_notification_events_event_type", "notification_events", ["event_type"])
    op.create_index(
        "ix_notification_events_collection_occurred",
        "notification_events",
        ["collection_uuid", "occurred_at"],
    )
    op.create_index(
        "ix_notification_events_type_occurred",
        "notification_events",
        ["event_type", "occurred_at"],
    )

    op.create_table(
        "notification_outbox",
        sa.Column("outbox_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notification_events.event_id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_notification_outbox_pending",
        "notification_outbox",
        ["available_at"],
        postgresql_where=sa.text("published_at is null"),
    )

    op.create_table(
        "notification_deliveries",
        sa.Column("notification_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notification_events.event_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("recipient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "state",
            postgresql.ENUM(
                "unread", "read", "archived", name="notification_delivery_state", create_type=False
            ),
            nullable=False,
            server_default="unread",
        ),
        sa.Column(
            "delivery_seq",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "delivered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_notification_deliveries_event_id", "notification_deliveries", ["event_id"]
    )
    op.create_index(
        "ix_notification_deliveries_recipient_id", "notification_deliveries", ["recipient_id"]
    )
    op.create_index("ix_notification_deliveries_state", "notification_deliveries", ["state"])
    op.create_index(
        "uq_notification_delivery_event_recipient",
        "notification_deliveries",
        ["event_id", "recipient_id"],
        unique=True,
    )
    op.create_index(
        "ix_notification_deliveries_recipient_state_delivered",
        "notification_deliveries",
        ["recipient_id", "state", "delivered_at"],
    )


def downgrade() -> None:
    op.drop_table("notification_deliveries")
    op.drop_table("notification_outbox")
    op.drop_table("notification_events")
    postgresql.ENUM(name="notification_delivery_state").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="notification_severity").drop(op.get_bind(), checkfirst=True)
