"""Add tracking list fields for delivery point accounts.

Revision ID: dp_accounts_004
Revises: dp_accounts_003
Create Date: 2026-03-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "dp_accounts_004"
down_revision: Union[str, None] = "dp_accounts_003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "delivery_point_accounts",
        sa.Column("tracking_list_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "delivery_point_accounts",
        sa.Column("tracking_list_description", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("delivery_point_accounts", "tracking_list_description")
    op.drop_column("delivery_point_accounts", "tracking_list_name")
