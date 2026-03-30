"""Add email for delivery point accounts.

Revision ID: dp_accounts_003
Revises: dp_accounts_002
Create Date: 2026-03-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "dp_accounts_003"
down_revision: Union[str, None] = "dp_accounts_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("delivery_point_accounts", sa.Column("email", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("delivery_point_accounts", "email")
