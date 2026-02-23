"""Add driver delivery task and DC allocation tables

Revision ID: w7x8y9z0a1b2
Revises: fix_dc_seq_01
Create Date: 2026-02-16

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "w7x8y9z0a1b2"
down_revision: Union[str, None] = "fix_dc_seq_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create delivery_order_item_dc_allocations, delivery_order_item_dc_status,
    driver_delivery_tasks, driver_task_dc_deliveries.
    """
    op.create_table(
        "delivery_order_item_dc_allocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_item_id", sa.Integer(), nullable=False),
        sa.Column("dc_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dc_id"],
            ["geo_distribution_centers.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["order_item_id"],
            ["delivery_order_items.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "order_item_id",
            "dc_id",
            name="uq_order_item_dc_allocation",
        ),
    )
    op.create_index(
        op.f("ix_delivery_order_item_dc_allocations_id"),
        "delivery_order_item_dc_allocations",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_delivery_order_item_dc_allocations_order_item_id",
        "delivery_order_item_dc_allocations",
        ["order_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_delivery_order_item_dc_allocations_dc_id",
        "delivery_order_item_dc_allocations",
        ["dc_id"],
        unique=False,
    )

    op.create_table(
        "delivery_order_item_dc_status",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_item_id", sa.Integer(), nullable=False),
        sa.Column("dc_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["dc_id"],
            ["geo_distribution_centers.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["order_item_id"],
            ["delivery_order_items.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "order_item_id",
            "dc_id",
            name="uq_order_item_dc_status",
        ),
    )
    op.create_index(
        op.f("ix_delivery_order_item_dc_status_id"),
        "delivery_order_item_dc_status",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_delivery_order_item_dc_status_order_item_id",
        "delivery_order_item_dc_status",
        ["order_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_delivery_order_item_dc_status_dc_id",
        "delivery_order_item_dc_status",
        ["dc_id"],
        unique=False,
    )
    op.create_index(
        "ix_delivery_order_item_dc_status_status",
        "delivery_order_item_dc_status",
        ["status"],
        unique=False,
    )

    op.create_table(
        "driver_delivery_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_lat", sa.Float(), nullable=False),
        sa.Column("warehouse_lon", sa.Float(), nullable=False),
        sa.Column(
            "driver_id",
            sa.UUID(),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("loading_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("in_transit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["driver_id"],
            ["driver_accounts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["delivery_orders.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_driver_delivery_tasks_id"),
        "driver_delivery_tasks",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_driver_delivery_tasks_order_id",
        "driver_delivery_tasks",
        ["order_id"],
        unique=False,
    )
    op.create_index(
        "ix_driver_delivery_tasks_driver_id",
        "driver_delivery_tasks",
        ["driver_id"],
        unique=False,
    )
    op.create_index(
        "ix_driver_delivery_tasks_status",
        "driver_delivery_tasks",
        ["status"],
        unique=False,
    )

    op.create_table(
        "driver_task_dc_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("dc_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["dc_id"],
            ["geo_distribution_centers.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["driver_delivery_tasks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "task_id",
            "dc_id",
            name="uq_task_dc_delivery",
        ),
    )
    op.create_index(
        op.f("ix_driver_task_dc_deliveries_id"),
        "driver_task_dc_deliveries",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_driver_task_dc_deliveries_task_id",
        "driver_task_dc_deliveries",
        ["task_id"],
        unique=False,
    )
    op.create_index(
        "ix_driver_task_dc_deliveries_dc_id",
        "driver_task_dc_deliveries",
        ["dc_id"],
        unique=False,
    )
    op.create_index(
        "ix_driver_task_dc_deliveries_status",
        "driver_task_dc_deliveries",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Drop driver task and allocation tables."""
    op.drop_index(
        op.f("ix_driver_task_dc_deliveries_status"),
        table_name="driver_task_dc_deliveries",
    )
    op.drop_index(
        op.f("ix_driver_task_dc_deliveries_dc_id"),
        table_name="driver_task_dc_deliveries",
    )
    op.drop_index(
        op.f("ix_driver_task_dc_deliveries_task_id"),
        table_name="driver_task_dc_deliveries",
    )
    op.drop_index(
        op.f("ix_driver_task_dc_deliveries_id"),
        table_name="driver_task_dc_deliveries",
    )
    op.drop_table("driver_task_dc_deliveries")

    op.drop_index(
        op.f("ix_driver_delivery_tasks_status"),
        table_name="driver_delivery_tasks",
    )
    op.drop_index(
        op.f("ix_driver_delivery_tasks_driver_id"),
        table_name="driver_delivery_tasks",
    )
    op.drop_index(
        op.f("ix_driver_delivery_tasks_order_id"),
        table_name="driver_delivery_tasks",
    )
    op.drop_index(
        op.f("ix_driver_delivery_tasks_id"),
        table_name="driver_delivery_tasks",
    )
    op.drop_table("driver_delivery_tasks")

    op.drop_index(
        op.f("ix_delivery_order_item_dc_status_status"),
        table_name="delivery_order_item_dc_status",
    )
    op.drop_index(
        op.f("ix_delivery_order_item_dc_status_dc_id"),
        table_name="delivery_order_item_dc_status",
    )
    op.drop_index(
        op.f("ix_delivery_order_item_dc_status_order_item_id"),
        table_name="delivery_order_item_dc_status",
    )
    op.drop_index(
        op.f("ix_delivery_order_item_dc_status_id"),
        table_name="delivery_order_item_dc_status",
    )
    op.drop_table("delivery_order_item_dc_status")

    op.drop_index(
        op.f("ix_delivery_order_item_dc_allocations_dc_id"),
        table_name="delivery_order_item_dc_allocations",
    )
    op.drop_index(
        op.f("ix_delivery_order_item_dc_allocations_order_item_id"),
        table_name="delivery_order_item_dc_allocations",
    )
    op.drop_index(
        op.f("ix_delivery_order_item_dc_allocations_id"),
        table_name="delivery_order_item_dc_allocations",
    )
    op.drop_table("delivery_order_item_dc_allocations")
