"""Add courier_last_location table

Revision ID: courier_loc_001
Revises: c4d5e6f7g8h9
Create Date: 2026-03-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "courier_loc_001"
down_revision: Union[str, None] = "c4d5e6f7g8h9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "courier_last_location",
        sa.Column("id", sa.Integer(), sa.Identity(always=False, start=1, increment=1), nullable=False),
        sa.Column("courier_id", PG_UUID(as_uuid=True), nullable=False),
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
            ["courier_id"],
            ["courier_accounts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("courier_id", "delivery_order_id", name="uq_courier_order_location"),
    )
    op.create_index(
        op.f("ix_courier_last_location_id"),
        "courier_last_location",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_courier_last_location_courier_id",
        "courier_last_location",
        ["courier_id"],
        unique=False,
    )
    op.create_index(
        "ix_courier_last_location_delivery_order_id",
        "courier_last_location",
        ["delivery_order_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_courier_last_location_delivery_order_id",
        table_name="courier_last_location",
    )
    op.drop_index(
        "ix_courier_last_location_courier_id",
        table_name="courier_last_location",
    )
    op.drop_index(
        op.f("ix_courier_last_location_id"),
        table_name="courier_last_location",
    )
    op.drop_table("courier_last_location")
