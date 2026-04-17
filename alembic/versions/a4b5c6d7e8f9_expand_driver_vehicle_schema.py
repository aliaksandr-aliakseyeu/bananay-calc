"""Expand driver vehicle schema with capabilities/compliance tables.

Revision ID: a4b5c6d7e8f9
Revises: z0a1b2c3d4e5
Create Date: 2026-04-15 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a4b5c6d7e8f9"
down_revision: Union[str, None] = "z0a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vehicle_capabilities",
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payload_kg", sa.Integer(), nullable=False),
        sa.Column("cargo_volume_m3", sa.Numeric(8, 3), nullable=True),
        sa.Column("cargo_length_mm", sa.Integer(), nullable=True),
        sa.Column("cargo_width_mm", sa.Integer(), nullable=True),
        sa.Column("cargo_height_mm", sa.Integer(), nullable=True),
        sa.Column("max_cargo_length_mm", sa.Integer(), nullable=True),
        sa.Column("max_cargo_weight_kg", sa.Integer(), nullable=True),
        sa.Column("banana_box_capacity", sa.SmallInteger(), nullable=True),
        sa.Column("banana_box_capacity_bucket", sa.SmallInteger(), nullable=True),
        sa.Column("has_refrigerator", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("min_temp_c", sa.Numeric(4, 1), nullable=True),
        sa.Column("max_temp_c", sa.Numeric(4, 1), nullable=True),
        sa.Column("supports_constant_temp", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("has_liftgate", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("has_ramp", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("has_straps", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("has_antislip_floor", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("allows_chilled_food", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("allows_frozen_food", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("allows_perishable_goods", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("allows_fmcg", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("allows_hazardous_goods", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("hazard_class", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["vehicle_id"], ["driver_vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("vehicle_id"),
        sa.CheckConstraint("payload_kg > 0", name="ck_vehicle_capabilities_payload_positive"),
        sa.CheckConstraint(
            "cargo_volume_m3 IS NULL OR cargo_volume_m3 > 0",
            name="ck_vehicle_capabilities_volume_positive",
        ),
        sa.CheckConstraint(
            "cargo_length_mm IS NULL OR cargo_length_mm > 0",
            name="ck_vehicle_capabilities_length_positive",
        ),
        sa.CheckConstraint(
            "cargo_width_mm IS NULL OR cargo_width_mm > 0",
            name="ck_vehicle_capabilities_width_positive",
        ),
        sa.CheckConstraint(
            "cargo_height_mm IS NULL OR cargo_height_mm > 0",
            name="ck_vehicle_capabilities_height_positive",
        ),
        sa.CheckConstraint(
            "max_cargo_length_mm IS NULL OR max_cargo_length_mm > 0",
            name="ck_vehicle_capabilities_max_length_positive",
        ),
        sa.CheckConstraint(
            "max_cargo_weight_kg IS NULL OR max_cargo_weight_kg > 0",
            name="ck_vehicle_capabilities_max_weight_positive",
        ),
        sa.CheckConstraint(
            "banana_box_capacity IS NULL OR banana_box_capacity >= 0",
            name="ck_vehicle_capabilities_box_capacity_non_negative",
        ),
        sa.CheckConstraint(
            "banana_box_capacity_bucket IS NULL OR banana_box_capacity_bucket >= 0",
            name="ck_vehicle_capabilities_box_bucket_non_negative",
        ),
        sa.CheckConstraint(
            "("
            "has_refrigerator = FALSE AND min_temp_c IS NULL AND max_temp_c IS NULL"
            ") OR ("
            "has_refrigerator = TRUE AND min_temp_c IS NOT NULL AND max_temp_c IS NOT NULL AND min_temp_c <= max_temp_c"
            ")",
            name="ck_vehicle_capabilities_temperature_consistency",
        ),
    )
    op.create_index("ix_vehicle_capabilities_payload_kg", "vehicle_capabilities", ["payload_kg"], unique=False)
    op.create_index(
        "ix_vehicle_capabilities_has_refrigerator",
        "vehicle_capabilities",
        ["has_refrigerator"],
        unique=False,
    )
    op.create_index(
        "ix_vehicle_capabilities_banana_box_capacity",
        "vehicle_capabilities",
        ["banana_box_capacity"],
        unique=False,
    )

    op.create_table(
        "vehicle_compliance",
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("insurance_valid_until", sa.Date(), nullable=True),
        sa.Column("last_inspection_date", sa.Date(), nullable=True),
        sa.Column("sts_number", sa.String(length=100), nullable=True),
        sa.Column("verification_status", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["vehicle_id"], ["driver_vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("vehicle_id"),
    )

    op.add_column("driver_vehicles", sa.Column("plate_number_normalized", sa.String(length=20), nullable=True))
    op.add_column("driver_vehicles", sa.Column("brand", sa.String(length=255), nullable=True))
    op.add_column("driver_vehicles", sa.Column("vin", sa.String(length=32), nullable=True))
    op.add_column("driver_vehicles", sa.Column("year", sa.SmallInteger(), nullable=True))
    op.add_column("driver_vehicles", sa.Column("body_type_code", sa.SmallInteger(), nullable=True))
    op.add_column(
        "driver_vehicles",
        sa.Column("status", sa.SmallInteger(), nullable=False, server_default="1"),
    )
    op.create_index(
        "ix_driver_vehicles_plate_number_normalized",
        "driver_vehicles",
        ["plate_number_normalized"],
        unique=False,
    )
    op.create_index(
        "ix_driver_vehicles_driver_id_status",
        "driver_vehicles",
        ["driver_id", "status"],
        unique=False,
    )
    op.create_index(
        "idx_driver_vehicles_driver_active",
        "driver_vehicles",
        ["driver_id"],
        unique=False,
        postgresql_where=sa.text("is_active = TRUE"),
    )

    op.add_column(
        "media_files",
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column("media_files", sa.Column("superseded_by_media_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("media_files", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_media_files_superseded_by_media_id",
        "media_files",
        "media_files",
        ["superseded_by_media_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_media_files_superseded_by_media_id",
        "media_files",
        ["superseded_by_media_id"],
        unique=False,
    )
    op.create_index(
        "idx_media_files_not_current",
        "media_files",
        ["owner_type", "owner_id", "is_current"],
        unique=False,
        postgresql_where=sa.text("is_current = FALSE"),
    )

    op.execute(
        """
        UPDATE driver_vehicles
        SET plate_number_normalized = UPPER(
            REGEXP_REPLACE(COALESCE(plate_number, ''), '[^0-9A-Za-zА-Яа-я]+', '', 'g')
        )
        WHERE plate_number_normalized IS NULL
        """
    )
    op.execute(
        """
        UPDATE driver_vehicles
        SET status = CASE
            WHEN is_active = TRUE THEN 1
            ELSE 5
        END
        """
    )
    op.execute(
        """
        UPDATE driver_vehicles
        SET body_type_code = CASE
            WHEN body_type IS NULL OR btrim(body_type) = '' THEN 0
            WHEN lower(body_type) LIKE '%%реф%%' OR lower(body_type) LIKE '%%fridge%%' OR lower(body_type) LIKE '%%refriger%%' OR lower(body_type) LIKE '%%cold%%' THEN 2
            WHEN lower(body_type) LIKE '%%изотерм%%' OR lower(body_type) LIKE '%%isotherm%%' THEN 6
            WHEN lower(body_type) LIKE '%%тент%%' OR lower(body_type) LIKE '%%tent%%' OR lower(body_type) LIKE '%%curtain%%' THEN 3
            WHEN lower(body_type) LIKE '%%фург%%' OR lower(body_type) LIKE '%%van%%' THEN 1
            WHEN lower(body_type) LIKE '%%box%%' OR lower(body_type) LIKE '%%будк%%' THEN 4
            WHEN lower(body_type) LIKE '%%борт%%' OR lower(body_type) LIKE '%%flatbed%%' OR lower(body_type) LIKE '%%platform%%' THEN 5
            ELSE 99
        END
        WHERE body_type_code IS NULL
        """
    )

    op.execute(
        """
        INSERT INTO vehicle_capabilities (
            vehicle_id,
            payload_kg,
            cargo_volume_m3,
            updated_at
        )
        SELECT
            id,
            capacity_kg,
            capacity_m3,
            updated_at
        FROM driver_vehicles dv
        WHERE NOT EXISTS (
            SELECT 1
            FROM vehicle_capabilities vc
            WHERE vc.vehicle_id = dv.id
        )
        """
    )
    op.execute(
        """
        INSERT INTO vehicle_compliance (
            vehicle_id,
            verification_status,
            updated_at
        )
        SELECT
            id,
            0,
            updated_at
        FROM driver_vehicles dv
        WHERE NOT EXISTS (
            SELECT 1
            FROM vehicle_compliance vc
            WHERE vc.vehicle_id = dv.id
        )
        """
    )

    op.execute(
        """
        UPDATE media_files
        SET is_current = FALSE
        WHERE owner_type = 'vehicle'
          AND kind IN ('photo', 'sts')
          AND id NOT IN (
            SELECT photo_media_id
            FROM driver_vehicles
            WHERE photo_media_id IS NOT NULL
            UNION
            SELECT sts_media_id
            FROM driver_vehicles
            WHERE sts_media_id IS NOT NULL
          )
        """
    )
    op.execute(
        """
        UPDATE media_files mf
        SET superseded_by_media_id = dv.photo_media_id
        FROM driver_vehicles dv
        WHERE mf.owner_type = 'vehicle'
          AND mf.kind = 'photo'
          AND mf.owner_id = dv.id
          AND dv.photo_media_id IS NOT NULL
          AND mf.id <> dv.photo_media_id
        """
    )
    op.execute(
        """
        UPDATE media_files mf
        SET superseded_by_media_id = dv.sts_media_id
        FROM driver_vehicles dv
        WHERE mf.owner_type = 'vehicle'
          AND mf.kind = 'sts'
          AND mf.owner_id = dv.id
          AND dv.sts_media_id IS NOT NULL
          AND mf.id <> dv.sts_media_id
        """
    )


def downgrade() -> None:
    op.drop_index("idx_media_files_not_current", table_name="media_files")
    op.drop_index("ix_media_files_superseded_by_media_id", table_name="media_files")
    op.drop_constraint("fk_media_files_superseded_by_media_id", "media_files", type_="foreignkey")
    op.drop_column("media_files", "deleted_at")
    op.drop_column("media_files", "superseded_by_media_id")
    op.drop_column("media_files", "is_current")

    op.drop_index("idx_driver_vehicles_driver_active", table_name="driver_vehicles")
    op.drop_index("ix_driver_vehicles_driver_id_status", table_name="driver_vehicles")
    op.drop_index("ix_driver_vehicles_plate_number_normalized", table_name="driver_vehicles")
    op.drop_column("driver_vehicles", "status")
    op.drop_column("driver_vehicles", "body_type_code")
    op.drop_column("driver_vehicles", "year")
    op.drop_column("driver_vehicles", "vin")
    op.drop_column("driver_vehicles", "brand")
    op.drop_column("driver_vehicles", "plate_number_normalized")

    op.drop_table("vehicle_compliance")
    op.drop_index("ix_vehicle_capabilities_banana_box_capacity", table_name="vehicle_capabilities")
    op.drop_index("ix_vehicle_capabilities_has_refrigerator", table_name="vehicle_capabilities")
    op.drop_index("ix_vehicle_capabilities_payload_kg", table_name="vehicle_capabilities")
    op.drop_table("vehicle_capabilities")
