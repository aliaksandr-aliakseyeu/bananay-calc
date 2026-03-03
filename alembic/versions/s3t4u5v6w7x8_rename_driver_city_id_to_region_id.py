"""Rename driver_accounts.city_id to region_id

Revision ID: s3t4u5v6w7x8
Revises: r2s3t4u5v6w7
Create Date: 2026-02-09 17:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "s3t4u5v6w7x8"
down_revision: Union[str, None] = "r2s3t4u5v6w7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_driver_accounts_status_city_id", table_name="driver_accounts")
    op.alter_column(
        "driver_accounts",
        "city_id",
        new_column_name="region_id",
        existing_type=sa.Integer(),
        existing_nullable=True,
    )
    op.create_index(
        "ix_driver_accounts_status_region_id",
        "driver_accounts",
        ["status", "region_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_driver_accounts_status_region_id", table_name="driver_accounts")
    op.alter_column(
        "driver_accounts",
        "region_id",
        new_column_name="city_id",
        existing_type=sa.Integer(),
        existing_nullable=True,
    )
    op.create_index(
        "ix_driver_accounts_status_city_id",
        "driver_accounts",
        ["status", "city_id"],
        unique=False,
    )
