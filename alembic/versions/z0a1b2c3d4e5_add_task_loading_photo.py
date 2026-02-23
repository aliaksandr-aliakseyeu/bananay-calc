"""Add loading photo to driver delivery task (media_owner_uuid, loading_photo_media_id)

Revision ID: z0a1b2c3d4e5
Revises: y9z0a1b2c3d4
Create Date: 2026-02-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "z0a1b2c3d4e5"
down_revision: Union[str, None] = "y9z0a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            ALTER TYPE mediafileownertype ADD VALUE 'driver_delivery_task';
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.add_column(
        "driver_delivery_tasks",
        sa.Column("media_owner_uuid", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "driver_delivery_tasks",
        sa.Column("loading_photo_media_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_driver_delivery_tasks_media_owner_uuid"),
        "driver_delivery_tasks",
        ["media_owner_uuid"],
        unique=False,
    )
    op.create_index(
        op.f("ix_driver_delivery_tasks_loading_photo_media_id"),
        "driver_delivery_tasks",
        ["loading_photo_media_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_driver_delivery_tasks_loading_photo_media_id_media_files",
        "driver_delivery_tasks",
        "media_files",
        ["loading_photo_media_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_driver_delivery_tasks_loading_photo_media_id_media_files",
        "driver_delivery_tasks",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_driver_delivery_tasks_loading_photo_media_id"),
        table_name="driver_delivery_tasks",
    )
    op.drop_index(
        op.f("ix_driver_delivery_tasks_media_owner_uuid"),
        table_name="driver_delivery_tasks",
    )
    op.drop_column("driver_delivery_tasks", "loading_photo_media_id")
    op.drop_column("driver_delivery_tasks", "media_owner_uuid")
    # PostgreSQL does not support removing enum values
    pass
