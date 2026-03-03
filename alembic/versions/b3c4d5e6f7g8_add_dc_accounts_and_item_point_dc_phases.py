"""Add DC accounts and extend item point scan phases for DC lifecycle.

Revision ID: b3c4d5e6f7g8
Revises: a2b3c4d5e6f7
Create Date: 2026-02-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b3c4d5e6f7g8"
down_revision: Union[str, None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    dc_account_status = sa.Enum(
        "draft",
        "active",
        "blocked",
        name="dcaccountstatus",
        native_enum=False,
    )
    dc_otp_status = sa.Enum(
        "pending",
        "used",
        name="dcotpstatus",
        native_enum=False,
    )

    op.create_table(
        "dc_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phone_e164", sa.String(length=20), nullable=False),
        sa.Column("status", dc_account_status, nullable=False, server_default="draft"),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("distribution_center_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("blocked_reason", sa.String(length=500), nullable=True),
        sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["distribution_center_id"], ["geo_distribution_centers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dc_accounts_id"), "dc_accounts", ["id"], unique=False)
    op.create_index(op.f("ix_dc_accounts_phone_e164"), "dc_accounts", ["phone_e164"], unique=True)
    op.create_index(op.f("ix_dc_accounts_status"), "dc_accounts", ["status"], unique=False)
    op.create_index(
        op.f("ix_dc_accounts_distribution_center_id"),
        "dc_accounts",
        ["distribution_center_id"],
        unique=False,
    )
    op.create_index(
        "ix_dc_accounts_status_distribution_center_id",
        "dc_accounts",
        ["status", "distribution_center_id"],
        unique=False,
    )

    op.create_table(
        "dc_otp_codes",
        sa.Column("phone_e164", sa.String(length=20), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("status", dc_otp_status, nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("phone_e164"),
    )
    op.create_index(op.f("ix_dc_otp_codes_status"), "dc_otp_codes", ["status"], unique=False)

    op.execute("ALTER TYPE itempointscanphase ADD VALUE IF NOT EXISTS 'received_at_dc'")
    op.execute("ALTER TYPE itempointscanphase ADD VALUE IF NOT EXISTS 'moved_to_sorting'")
    op.execute("ALTER TYPE itempointscanphase ADD VALUE IF NOT EXISTS 'sorted_to_zone'")
    op.execute("ALTER TYPE itempointscanphase ADD VALUE IF NOT EXISTS 'handed_to_courier2'")

    op.add_column(
        "delivery_order_item_point_scan_events",
        sa.Column("scanned_by_dc_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "delivery_order_item_point_scan_events",
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "delivery_order_item_point_scan_events",
        sa.Column("event_payload", sa.JSON(), nullable=True),
    )
    op.create_foreign_key(
        "fk_item_point_scan_events_scanned_by_dc_id",
        "delivery_order_item_point_scan_events",
        "dc_accounts",
        ["scanned_by_dc_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_delivery_order_item_point_scan_events_scanned_by_dc_id"),
        "delivery_order_item_point_scan_events",
        ["scanned_by_dc_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_delivery_order_item_point_scan_events_operation_id"),
        "delivery_order_item_point_scan_events",
        ["operation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_delivery_order_item_point_scan_events_operation_id"),
        table_name="delivery_order_item_point_scan_events",
    )
    op.drop_index(
        op.f("ix_delivery_order_item_point_scan_events_scanned_by_dc_id"),
        table_name="delivery_order_item_point_scan_events",
    )
    op.drop_constraint(
        "fk_item_point_scan_events_scanned_by_dc_id",
        "delivery_order_item_point_scan_events",
        type_="foreignkey",
    )
    op.drop_column("delivery_order_item_point_scan_events", "event_payload")
    op.drop_column("delivery_order_item_point_scan_events", "operation_id")
    op.drop_column("delivery_order_item_point_scan_events", "scanned_by_dc_id")

    op.drop_index(op.f("ix_dc_otp_codes_status"), table_name="dc_otp_codes")
    op.drop_table("dc_otp_codes")

    op.drop_index("ix_dc_accounts_status_distribution_center_id", table_name="dc_accounts")
    op.drop_index(op.f("ix_dc_accounts_distribution_center_id"), table_name="dc_accounts")
    op.drop_index(op.f("ix_dc_accounts_status"), table_name="dc_accounts")
    op.drop_index(op.f("ix_dc_accounts_phone_e164"), table_name="dc_accounts")
    op.drop_index(op.f("ix_dc_accounts_id"), table_name="dc_accounts")
    op.drop_table("dc_accounts")
