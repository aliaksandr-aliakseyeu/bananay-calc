"""Add qr_token to delivery_order_item_points and delivery_order_item_point_scan_events table

Revision ID: a2b3c4d5e6f7
Revises: z1a2b3c4d5e6
Create Date: 2026-02-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "z1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Add qr_token to delivery_order_item_points (existing rows get UUID via server_default)
    op.add_column(
        "delivery_order_item_points",
        sa.Column(
            "qr_token",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
    )
    op.create_index(
        op.f("ix_delivery_order_item_points_qr_token"),
        "delivery_order_item_points",
        ["qr_token"],
        unique=True,
    )

    # 2) Create enum for scan phase (extensible: loading, at_dc, etc.)
    item_point_scan_phase = postgresql.ENUM(
        "loading",
        name="itempointscanphase",
        create_type=True,
    )
    item_point_scan_phase.create(op.get_bind(), checkfirst=True)
    # Use same type for column without auto-create (type already exists)
    phase_column_type = postgresql.ENUM(
        "loading",
        name="itempointscanphase",
        create_type=False,
    )

    # 3) Create scan events audit table
    op.create_table(
        "delivery_order_item_point_scan_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "delivery_order_item_point_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "phase",
            phase_column_type,
            nullable=False,
        ),
        sa.Column(
            "scanned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "scanned_by_driver_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["delivery_order_item_point_id"],
            ["delivery_order_item_points.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scanned_by_driver_id"],
            ["driver_accounts.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_delivery_order_item_point_scan_events_id"),
        "delivery_order_item_point_scan_events",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_delivery_order_item_point_scan_events_delivery_order_item_point_id"),
        "delivery_order_item_point_scan_events",
        ["delivery_order_item_point_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_delivery_order_item_point_scan_events_phase"),
        "delivery_order_item_point_scan_events",
        ["phase"],
        unique=False,
    )
    op.create_index(
        op.f("ix_delivery_order_item_point_scan_events_scanned_at"),
        "delivery_order_item_point_scan_events",
        ["scanned_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_delivery_order_item_point_scan_events_scanned_by_driver_id"),
        "delivery_order_item_point_scan_events",
        ["scanned_by_driver_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_delivery_order_item_point_scan_events_scanned_by_driver_id"),
        table_name="delivery_order_item_point_scan_events",
    )
    op.drop_index(
        op.f("ix_delivery_order_item_point_scan_events_scanned_at"),
        table_name="delivery_order_item_point_scan_events",
    )
    op.drop_index(
        op.f("ix_delivery_order_item_point_scan_events_phase"),
        table_name="delivery_order_item_point_scan_events",
    )
    op.drop_index(
        op.f("ix_delivery_order_item_point_scan_events_delivery_order_item_point_id"),
        table_name="delivery_order_item_point_scan_events",
    )
    op.drop_index(
        op.f("ix_delivery_order_item_point_scan_events_id"),
        table_name="delivery_order_item_point_scan_events",
    )
    op.drop_table("delivery_order_item_point_scan_events")

    postgresql.ENUM(name="itempointscanphase").drop(op.get_bind(), checkfirst=True)

    op.drop_index(
        op.f("ix_delivery_order_item_points_qr_token"),
        table_name="delivery_order_item_points",
    )
    op.drop_column("delivery_order_item_points", "qr_token")
