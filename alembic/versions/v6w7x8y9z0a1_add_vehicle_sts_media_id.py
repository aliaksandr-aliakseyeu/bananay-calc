"""Add sts_media_id (СТС) to driver_vehicles

Revision ID: v6w7x8y9z0a1
Revises: u5v6w7x8y9z0
Create Date: 2026-02-09 20:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "v6w7x8y9z0a1"
down_revision: Union[str, None] = "u5v6w7x8y9z0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "driver_vehicles",
        sa.Column("sts_media_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_driver_vehicles_sts_media_id_media_files",
        "driver_vehicles",
        "media_files",
        ["sts_media_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_driver_vehicles_sts_media_id",
        "driver_vehicles",
        ["sts_media_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_driver_vehicles_sts_media_id", "driver_vehicles")
    op.drop_constraint(
        "fk_driver_vehicles_sts_media_id_media_files",
        "driver_vehicles",
        type_="foreignkey",
    )
    op.drop_column("driver_vehicles", "sts_media_id")
