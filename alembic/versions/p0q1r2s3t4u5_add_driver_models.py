"""Add driver models (accounts, vehicles, applications, media, OTP)

Revision ID: p0q1r2s3t4u5
Revises: o9p0q1r2s3t4
Create Date: 2026-02-09 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "p0q1r2s3t4u5"
down_revision: Union[str, None] = "o9p0q1r2s3t4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create driver-related enums and tables."""

    enums_to_create = [
        ("driveraccountstatus", "draft", "pending_review", "active", "blocked"),
        ("driverapplicationstatus", "draft", "pending_review", "approved", "rejected"),
        ("mediafileownertype", "driver", "application", "shift", "route_step"),
        ("driverotpstatus", "pending", "used"),
    ]
    for row in enums_to_create:
        name, *values = row
        vals = ", ".join(f"'{v}'" for v in values)
        stmt = f"CREATE TYPE {name} AS ENUM ({vals})"
        stmt_escaped = stmt.replace("'", "''")
        op.execute(
            f"DO $$ BEGIN "
            f"IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{name}') THEN "
            f"EXECUTE '{stmt_escaped}'; "
            f"END IF; END $$;"
        )

    driver_account_status = postgresql.ENUM(
        "draft",
        "pending_review",
        "active",
        "blocked",
        name="driveraccountstatus",
        create_type=False,
    )

    op.create_table(
        "driver_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phone_e164", sa.String(length=20), nullable=False),
        sa.Column(
            "status",
            driver_account_status,
            nullable=False,
            server_default="draft",
        ),
        sa.Column("full_name", sa.Text(), nullable=True),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("payout_account", sa.Text(), nullable=True),
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
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["city_id"], ["geo_regions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_driver_accounts_id"), "driver_accounts", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_driver_accounts_phone_e164"),
        "driver_accounts",
        ["phone_e164"],
        unique=True,
    )
    op.create_index(
        op.f("ix_driver_accounts_status"), "driver_accounts", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_driver_accounts_city_id"),
        "driver_accounts",
        ["city_id"],
        unique=False,
    )
    op.create_index(
        "ix_driver_accounts_status_city_id",
        "driver_accounts",
        ["status", "city_id"],
        unique=False,
    )

    driver_otp_status = postgresql.ENUM(
        "pending",
        "used",
        name="driverotpstatus",
        create_type=False,
    )

    op.create_table(
        "driver_otp_codes",
        sa.Column("phone_e164", sa.String(length=20), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column(
            "status",
            driver_otp_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("phone_e164"),
    )
    op.create_index(
        op.f("ix_driver_otp_codes_status"),
        "driver_otp_codes",
        ["status"],
        unique=False,
    )

    op.create_table(
        "driver_vehicles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plate_number", sa.String(length=20), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("capacity_kg", sa.Integer(), nullable=False),
        sa.Column("capacity_m3", sa.Numeric(6, 2), nullable=False),
        sa.Column("body_type", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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
        sa.ForeignKeyConstraint(
            ["driver_id"], ["driver_accounts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_driver_vehicles_id"), "driver_vehicles", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_driver_vehicles_driver_id"),
        "driver_vehicles",
        ["driver_id"],
        unique=False,
    )
    op.create_index(
        "ix_driver_vehicles_driver_id_is_active",
        "driver_vehicles",
        ["driver_id", "is_active"],
        unique=False,
    )

    driver_application_status = postgresql.ENUM(
        "draft",
        "pending_review",
        "approved",
        "rejected",
        name="driverapplicationstatus",
        create_type=False,
    )

    op.create_table(
        "driver_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            driver_application_status,
            nullable=False,
            server_default="draft",
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reject_reason", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["driver_id"], ["driver_accounts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"], ["geo_users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_driver_applications_id"),
        "driver_applications",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_driver_applications_driver_id"),
        "driver_applications",
        ["driver_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_driver_applications_status"),
        "driver_applications",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_driver_applications_reviewed_by"),
        "driver_applications",
        ["reviewed_by"],
        unique=False,
    )

    media_file_owner_type = postgresql.ENUM(
        "driver",
        "application",
        "shift",
        "route_step",
        name="mediafileownertype",
        create_type=False,
    )

    op.create_table(
        "media_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "owner_type",
            media_file_owner_type,
            nullable=False,
        ),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=100), nullable=False),
        sa.Column("blob_path", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_media_files_id"), "media_files", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_media_files_owner_type"),
        "media_files",
        ["owner_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_media_files_owner_id"),
        "media_files",
        ["owner_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_media_files_kind"),
        "media_files",
        ["kind"],
        unique=False,
    )
    op.create_index(
        "ix_media_files_owner_type_owner_id",
        "media_files",
        ["owner_type", "owner_id"],
        unique=False,
    )
    op.create_index(
        "ix_media_files_owner_type_owner_id_kind",
        "media_files",
        ["owner_type", "owner_id", "kind"],
        unique=False,
    )


def downgrade() -> None:
    """Drop driver tables and enums."""

    op.drop_index(
        "ix_media_files_owner_type_owner_id_kind",
        table_name="media_files",
    )
    op.drop_index(
        "ix_media_files_owner_type_owner_id",
        table_name="media_files",
    )
    op.drop_index(op.f("ix_media_files_kind"), table_name="media_files")
    op.drop_index(op.f("ix_media_files_owner_id"), table_name="media_files")
    op.drop_index(op.f("ix_media_files_owner_type"), table_name="media_files")
    op.drop_index(op.f("ix_media_files_id"), table_name="media_files")
    op.drop_table("media_files")

    op.drop_index(
        op.f("ix_driver_applications_reviewed_by"),
        table_name="driver_applications",
    )
    op.drop_index(
        op.f("ix_driver_applications_status"),
        table_name="driver_applications",
    )
    op.drop_index(
        op.f("ix_driver_applications_driver_id"),
        table_name="driver_applications",
    )
    op.drop_index(
        op.f("ix_driver_applications_id"),
        table_name="driver_applications",
    )
    op.drop_table("driver_applications")

    op.drop_index(
        "ix_driver_vehicles_driver_id_is_active",
        table_name="driver_vehicles",
    )
    op.drop_index(
        op.f("ix_driver_vehicles_driver_id"),
        table_name="driver_vehicles",
    )
    op.drop_index(op.f("ix_driver_vehicles_id"), table_name="driver_vehicles")
    op.drop_table("driver_vehicles")

    op.drop_index(op.f("ix_driver_otp_codes_status"), table_name="driver_otp_codes")
    op.drop_table("driver_otp_codes")

    op.drop_index(
        "ix_driver_accounts_status_city_id",
        table_name="driver_accounts",
    )
    op.drop_index(op.f("ix_driver_accounts_city_id"), table_name="driver_accounts")
    op.drop_index(op.f("ix_driver_accounts_status"), table_name="driver_accounts")
    op.drop_index(op.f("ix_driver_accounts_phone_e164"), table_name="driver_accounts")
    op.drop_index(op.f("ix_driver_accounts_id"), table_name="driver_accounts")
    op.drop_table("driver_accounts")

    op.execute("DROP TYPE driverotpstatus")
    op.execute("DROP TYPE mediafileownertype")
    op.execute("DROP TYPE driverapplicationstatus")
    op.execute("DROP TYPE driveraccountstatus")
