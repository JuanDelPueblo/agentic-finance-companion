"""create initial schema

Revision ID: 0001
Create Date: 2026-11-06 18:54:31.768943

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("auth_subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "financial_states",
        sa.Column("state_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("input_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("engine_version", sa.String(length=20), nullable=False),
        sa.Column("state_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column(
            "computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
        ),
        sa.PrimaryKeyConstraint("state_id"),
    )
    op.create_table(
        "goals",
        sa.Column("goal_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("target_amount", sa.Numeric(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
        ),
        sa.PrimaryKeyConstraint("goal_id"),
    )
    op.create_table(
        "plaid_items",
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("plaid_item_ref", sa.String(length=128), nullable=False),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("institution_name", sa.String(length=120), nullable=True),
        sa.Column("connection_status", sa.String(length=30), nullable=False),
        sa.Column("sync_cursor", sa.Text(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
        ),
        sa.PrimaryKeyConstraint("item_id"),
    )
    op.create_table(
        "user_context",
        sa.Column("context_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("context_key", sa.String(length=60), nullable=False),
        sa.Column("context_value", postgresql.JSONB(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column(
            "provided_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
        ),
        sa.PrimaryKeyConstraint("context_id"),
    )
    op.create_table(
        "accounts",
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("plaid_account_ref", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("account_type", sa.String(length=30), nullable=False),
        sa.Column("account_subtype", sa.String(length=30), nullable=True),
        sa.Column("current_balance", sa.Numeric(), nullable=True),
        sa.Column("available_balance", sa.Numeric(), nullable=True),
        sa.Column("currency_code", sa.CHAR(length=3), nullable=True),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["plaid_items.item_id"],
        ),
        sa.PrimaryKeyConstraint("account_id"),
    )
    op.create_table(
        "plans",
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("state_id", sa.Uuid(), nullable=False),
        sa.Column("trigger_reason", sa.String(length=60), nullable=False),
        sa.Column("plan_body", postgresql.JSONB(), nullable=False),
        sa.Column("model_name", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["state_id"],
            ["financial_states.state_id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
        ),
        sa.PrimaryKeyConstraint("plan_id"),
    )
    op.create_table(
        "webhook_events",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("webhook_type", sa.String(length=40), nullable=False),
        sa.Column("webhook_code", sa.String(length=60), nullable=False),
        sa.Column(
            "received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["plaid_items.item_id"],
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_table(
        "chat_messages",
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["plans.plan_id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
        ),
        sa.PrimaryKeyConstraint("message_id"),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_type", sa.String(length=60), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "run_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("webhook_event_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["webhook_event_id"],
            ["webhook_events.event_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "plan_validations",
        sa.Column("validation_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("violations", postgresql.JSONB(), nullable=False),
        sa.Column("validator_version", sa.String(length=20), nullable=False),
        sa.Column(
            "validated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["plans.plan_id"],
        ),
        sa.PrimaryKeyConstraint("validation_id"),
    )
    op.create_table(
        "transactions",
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("plaid_transaction_ref", sa.String(length=128), nullable=False),
        sa.Column("amount", sa.Numeric(), nullable=False),
        sa.Column("posted_date", sa.Date(), nullable=False),
        sa.Column("merchant_name", sa.String(length=160), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("sync_state", sa.String(length=20), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.account_id"],
        ),
        sa.PrimaryKeyConstraint("transaction_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("transactions")
    op.drop_table("plan_validations")
    op.drop_table("jobs")
    op.drop_table("chat_messages")
    op.drop_table("webhook_events")
    op.drop_table("plans")
    op.drop_table("accounts")
    op.drop_table("user_context")
    op.drop_table("plaid_items")
    op.drop_table("goals")
    op.drop_table("financial_states")
    op.drop_table("users")
