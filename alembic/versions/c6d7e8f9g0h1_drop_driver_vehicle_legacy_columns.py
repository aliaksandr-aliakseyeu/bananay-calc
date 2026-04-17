"""Drop legacy driver vehicle columns now covered by normalized schema.

Revision ID: c6d7e8f9g0h1
Revises: b5c6d7e8f9g0
Create Date: 2026-04-15 15:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c6d7e8f9g0h1"
down_revision: Union[str, None] = "b5c6d7e8f9g0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("idx_driver_vehicles_driver_active", table_name="driver_vehicles")
    op.drop_index("ix_driver_vehicles_driver_id_is_active", table_name="driver_vehicles")
    op.create_index(
        "idx_driver_vehicles_driver_status_operational",
        "driver_vehicles",
        ["driver_id", "status"],
        unique=False,
        postgresql_where=sa.text("status IN (1, 2, 3)"),
    )
    op.drop_column("driver_vehicles", "is_active")
    op.drop_column("driver_vehicles", "body_type")
    op.drop_column("driver_vehicles", "capacity_m3")
    op.drop_column("driver_vehicles", "capacity_kg")


def downgrade() -> None:
    op.add_column(
        "driver_vehicles",
        sa.Column("capacity_kg", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "driver_vehicles",
        sa.Column("capacity_m3", sa.Numeric(6, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "driver_vehicles",
        sa.Column("body_type", sa.Text(), nullable=True),
    )
    op.add_column(
        "driver_vehicles",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.drop_index("idx_driver_vehicles_driver_status_operational", table_name="driver_vehicles")
    op.create_index(
        "ix_driver_vehicles_driver_id_is_active",
        "driver_vehicles",
        ["driver_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "idx_driver_vehicles_driver_active",
        "driver_vehicles",
        ["driver_id"],
        unique=False,
        postgresql_where=sa.text("is_active = TRUE"),
    )
