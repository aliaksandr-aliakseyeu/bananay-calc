"""Add vehicle photo (MediaFileOwnerType.VEHICLE, driver_vehicles.photo_media_id)

Revision ID: u5v6w7x8y9z0
Revises: t4u5v6w7x8y9
Create Date: 2026-02-09 19:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "u5v6w7x8y9z0"
down_revision: Union[str, None] = "t4u5v6w7x8y9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE mediafileownertype ADD VALUE IF NOT EXISTS 'vehicle'")
    op.add_column(
        "driver_vehicles",
        sa.Column("photo_media_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_driver_vehicles_photo_media_id_media_files",
        "driver_vehicles",
        "media_files",
        ["photo_media_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_driver_vehicles_photo_media_id",
        "driver_vehicles",
        ["photo_media_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_driver_vehicles_photo_media_id", "driver_vehicles")
    op.drop_constraint(
        "fk_driver_vehicles_photo_media_id_media_files",
        "driver_vehicles",
        type_="foreignkey",
    )
    op.drop_column("driver_vehicles", "photo_media_id")
    # Note: PostgreSQL does not support removing enum values easily; leave 'vehicle' in type
