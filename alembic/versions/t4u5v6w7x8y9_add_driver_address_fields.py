"""Add address fields (street, building, apartment) to driver_accounts

Revision ID: t4u5v6w7x8y9
Revises: s3t4u5v6w7x8
Create Date: 2026-02-09 18:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "t4u5v6w7x8y9"
down_revision: Union[str, None] = "s3t4u5v6w7x8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "driver_accounts",
        sa.Column("street", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "driver_accounts",
        sa.Column("building", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "driver_accounts",
        sa.Column("apartment", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("driver_accounts", "apartment")
    op.drop_column("driver_accounts", "building")
    op.drop_column("driver_accounts", "street")
