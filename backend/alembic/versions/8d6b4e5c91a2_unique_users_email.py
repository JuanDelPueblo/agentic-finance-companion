"""Require unique email addresses for login.

Revision ID: 8d6b4e5c91a2
Revises: 413003bcee03
"""

from collections.abc import Sequence

from alembic import op

revision: str = "8d6b4e5c91a2"
down_revision: str | Sequence[str] | None = "413003bcee03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint("uq_users_email", "users", ["email"])


def downgrade() -> None:
    op.drop_constraint("uq_users_email", "users", type_="unique")
