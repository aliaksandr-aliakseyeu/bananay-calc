"""Add driver_last_location table

Revision ID: x8y9z0a1b2c3
Revises: w7x8y9z0a1b2
Create Date: 2026-02-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "x8y9z0a1b2c3"
down_revision: Union[str, None] = "w7x8y9z0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "driver_last_location",
        sa.Column("id", sa.Integer(), sa.Identity(always=False, start=1, increment=1), nullable=False),
        sa.Column("driver_id", PG_UUID(as_uuid=True), nullable=False),
        sa.Column("delivery_order_id", sa.Integer(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("device_info", sa.String(length=255), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["delivery_order_id"],
            ["delivery_orders.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["driver_id"],
            ["driver_accounts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("driver_id", "delivery_order_id", name="uq_driver_order_location"),
    )
    op.create_index(
        op.f("ix_driver_last_location_id"),
        "driver_last_location",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_driver_last_location_driver_id",
        "driver_last_location",
        ["driver_id"],
        unique=False,
    )
    op.create_index(
        "ix_driver_last_location_delivery_order_id",
        "driver_last_location",
        ["delivery_order_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_driver_last_location_delivery_order_id",
        table_name="driver_last_location",
    )
    op.drop_index(
        "ix_driver_last_location_driver_id",
        table_name="driver_last_location",
    )
    op.drop_index(
        op.f("ix_driver_last_location_id"),
        table_name="driver_last_location",
    )
    op.drop_table("driver_last_location")
