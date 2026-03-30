"""Add delivery point account auth tables.

Revision ID: dp_accounts_001
Revises: courier_loc_001
Create Date: 2026-03-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "dp_accounts_001"
down_revision: Union[str, None] = "courier_loc_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "delivery_point_accounts",
        sa.Column("id", PG_UUID(as_uuid=True), nullable=False),
        sa.Column("phone_e164", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone_e164"),
    )
    op.create_index("ix_delivery_point_accounts_id", "delivery_point_accounts", ["id"], unique=False)
    op.create_index(
        "ix_delivery_point_accounts_phone_e164",
        "delivery_point_accounts",
        ["phone_e164"],
        unique=True,
    )
    op.create_index("ix_delivery_point_accounts_status", "delivery_point_accounts", ["status"], unique=False)

    op.create_table(
        "delivery_point_account_points",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", PG_UUID(as_uuid=True), nullable=False),
        sa.Column("delivery_point_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["account_id"], ["delivery_point_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["delivery_point_id"], ["geo_delivery_points.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "delivery_point_id", name="uq_delivery_point_account_point"),
    )
    op.create_index(
        "ix_delivery_point_account_points_id", "delivery_point_account_points", ["id"], unique=False
    )
    op.create_index(
        "ix_delivery_point_account_points_account_id",
        "delivery_point_account_points",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        "ix_delivery_point_account_points_delivery_point_id",
        "delivery_point_account_points",
        ["delivery_point_id"],
        unique=False,
    )

    op.create_table(
        "delivery_point_otp_codes",
        sa.Column("phone_e164", sa.String(length=20), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("phone_e164"),
    )
    op.create_index(
        "ix_delivery_point_otp_codes_status", "delivery_point_otp_codes", ["status"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_delivery_point_otp_codes_status", table_name="delivery_point_otp_codes")
    op.drop_table("delivery_point_otp_codes")

    op.drop_index("ix_delivery_point_account_points_delivery_point_id", table_name="delivery_point_account_points")
    op.drop_index("ix_delivery_point_account_points_account_id", table_name="delivery_point_account_points")
    op.drop_index("ix_delivery_point_account_points_id", table_name="delivery_point_account_points")
    op.drop_table("delivery_point_account_points")

    op.drop_index("ix_delivery_point_accounts_status", table_name="delivery_point_accounts")
    op.drop_index("ix_delivery_point_accounts_phone_e164", table_name="delivery_point_accounts")
    op.drop_index("ix_delivery_point_accounts_id", table_name="delivery_point_accounts")
    op.drop_table("delivery_point_accounts")
