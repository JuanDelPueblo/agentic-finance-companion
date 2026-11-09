"""Resync every item so stored transactions get transaction_code and category_detailed.

Plaid's sync cursor doesn't resend transactions it already sent. Clearing it makes the next
sync fetch every transaction again; the sync updates each row by its Plaid ID, so no
duplicates are created.

Revision ID: 0004
Revises: 1b810bddceff
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "1b810bddceff"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE plaid_items SET sync_cursor = NULL")


def downgrade() -> None:
    # Nothing to undo: the next sync sets a new cursor.
    pass
