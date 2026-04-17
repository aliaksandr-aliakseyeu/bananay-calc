"""Merge vehicle migration head with delivery point accounts head.

Revision ID: b5c6d7e8f9g0
Revises: a4b5c6d7e8f9, dp_accounts_004
Create Date: 2026-04-15 12:20:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "b5c6d7e8f9g0"
down_revision: Union[str, Sequence[str], None] = ("a4b5c6d7e8f9", "dp_accounts_004")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
