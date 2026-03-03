"""Add unload photo to driver task DC delivery (unload_photo_media_id)

Revision ID: z1a2b3c4d5e6
Revises: z0a1b2c3d4e5
Create Date: 2026-02-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "z1a2b3c4d5e6"
down_revision: Union[str, None] = "z0a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "driver_task_dc_deliveries",
        sa.Column("unload_photo_media_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_driver_task_dc_deliveries_unload_photo_media_id"),
        "driver_task_dc_deliveries",
        ["unload_photo_media_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_driver_task_dc_deliveries_unload_photo_media_id_media_files",
        "driver_task_dc_deliveries",
        "media_files",
        ["unload_photo_media_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_driver_task_dc_deliveries_unload_photo_media_id_media_files",
        "driver_task_dc_deliveries",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_driver_task_dc_deliveries_unload_photo_media_id"),
        table_name="driver_task_dc_deliveries",
    )
    op.drop_column("driver_task_dc_deliveries", "unload_photo_media_id")
