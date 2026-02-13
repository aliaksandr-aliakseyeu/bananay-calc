"""Add driver_telegram_bindings table for OTP via Telegram

Revision ID: q1r2s3t4u5v6
Revises: p0q1r2s3t4u5
Create Date: 2026-02-09 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "q1r2s3t4u5v6"
down_revision: Union[str, None] = "p0q1r2s3t4u5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "driver_telegram_bindings",
        sa.Column("phone_e164", sa.String(length=20), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
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
        sa.PrimaryKeyConstraint("phone_e164"),
    )
    op.create_index(
        op.f("ix_driver_telegram_bindings_telegram_chat_id"),
        "driver_telegram_bindings",
        ["telegram_chat_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_driver_telegram_bindings_telegram_chat_id"),
        table_name="driver_telegram_bindings",
    )
    op.drop_table("driver_telegram_bindings")
