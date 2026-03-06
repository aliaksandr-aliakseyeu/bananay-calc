"""Add courier accounts, vehicles, applications, daily check-ins, delivery tasks.

Revision ID: c4d5e6f7g8h9
Revises: b3c4d5e6f7g8
Create Date: 2026-03-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c4d5e6f7g8h9"
down_revision: Union[str, None] = "b3c4d5e6f7g8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    courier_account_status = sa.Enum(
        "draft",
        "pending_review",
        "active",
        "blocked",
        name="courieraccountstatus",
        native_enum=False,
    )
    courier_application_status = sa.Enum(
        "draft",
        "pending_review",
        "approved",
        "rejected",
        name="courierapplicationstatus",
        native_enum=False,
    )
    courier_otp_status = sa.Enum(
        "pending",
        "used",
        name="courierotpstatus",
        native_enum=False,
    )
    daily_checkin_status = sa.Enum(
        "pending",
        "pending_review",
        "approved",
        "rejected",
        "expired",
        name="dailycheckinstatus",
        native_enum=False,
    )
    daily_checkin_photo_kind = sa.Enum(
        "selfie",
        "vehicle_front",
        "vehicle_left",
        "vehicle_right",
        "vehicle_rear",
        "vehicle_cargo",
        name="dailycheckinphotokind",
        native_enum=False,
    )
    courier_task_status = sa.Enum(
        "assigned",
        "in_transit",
        "delivered",
        name="couriertaskstatus",
        native_enum=False,
    )

    # courier_accounts
    op.create_table(
        "courier_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phone_e164", sa.String(length=20), nullable=False),
        sa.Column("status", courier_account_status, nullable=False, server_default="draft"),
        sa.Column("full_name", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=255), nullable=True),
        sa.Column("street", sa.String(length=255), nullable=True),
        sa.Column("building", sa.String(length=50), nullable=True),
        sa.Column("apartment", sa.String(length=50), nullable=True),
        sa.Column("region_id", sa.Integer(), nullable=True),
        sa.Column("payout_account", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["region_id"], ["geo_regions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_courier_accounts_phone_e164"), "courier_accounts", ["phone_e164"], unique=True)
    op.create_index(op.f("ix_courier_accounts_status"), "courier_accounts", ["status"])
    op.create_index("ix_courier_accounts_status_region_id", "courier_accounts", ["status", "region_id"])
    op.create_index(op.f("ix_courier_accounts_region_id"), "courier_accounts", ["region_id"])

    # courier_otp_codes
    op.create_table(
        "courier_otp_codes",
        sa.Column("phone_e164", sa.String(length=20), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("status", courier_otp_status, nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("phone_e164"),
    )
    op.create_index(op.f("ix_courier_otp_codes_status"), "courier_otp_codes", ["status"])

    # courier_vehicles
    op.create_table(
        "courier_vehicles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("courier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plate_number", sa.String(length=20), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("capacity_kg", sa.Integer(), nullable=False),
        sa.Column("capacity_m3", sa.Numeric(6, 2), nullable=False),
        sa.Column("body_type", sa.String(length=50), nullable=True),
        sa.Column("photo_media_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sts_media_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["courier_id"], ["courier_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["photo_media_id"], ["media_files.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sts_media_id"], ["media_files.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_courier_vehicles_courier_id"), "courier_vehicles", ["courier_id"])
    op.create_index(op.f("ix_courier_vehicles_photo_media_id"), "courier_vehicles", ["photo_media_id"])
    op.create_index(op.f("ix_courier_vehicles_sts_media_id"), "courier_vehicles", ["sts_media_id"])
    op.create_index("ix_courier_vehicles_courier_id_is_active", "courier_vehicles", ["courier_id", "is_active"])

    # courier_applications
    op.create_table(
        "courier_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("courier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", courier_application_status, nullable=False, server_default="draft"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["courier_id"], ["courier_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["geo_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("courier_id"),
    )
    op.create_index(op.f("ix_courier_applications_courier_id"), "courier_applications", ["courier_id"])
    op.create_index(op.f("ix_courier_applications_reviewed_by"), "courier_applications", ["reviewed_by"])
    op.create_index(op.f("ix_courier_applications_status"), "courier_applications", ["status"])

    # courier_daily_checkins
    op.create_table(
        "courier_daily_checkins",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("courier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("check_date", sa.Date(), nullable=False),
        sa.Column("status", daily_checkin_status, nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["courier_id"], ["courier_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["courier_vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("courier_id", "vehicle_id", "check_date", name="uq_courier_daily_checkin_courier_vehicle_date"),
    )
    op.create_index(op.f("ix_courier_daily_checkins_courier_id"), "courier_daily_checkins", ["courier_id"])
    op.create_index(op.f("ix_courier_daily_checkins_vehicle_id"), "courier_daily_checkins", ["vehicle_id"])
    op.create_index(op.f("ix_courier_daily_checkins_check_date"), "courier_daily_checkins", ["check_date"])
    op.create_index("ix_courier_daily_checkins_courier_date", "courier_daily_checkins", ["courier_id", "check_date"])
    op.create_index("ix_courier_daily_checkins_status", "courier_daily_checkins", ["status"])

    # courier_daily_checkin_photos
    op.create_table(
        "courier_daily_checkin_photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checkin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", daily_checkin_photo_kind, nullable=False),
        sa.Column("media_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["checkin_id"], ["courier_daily_checkins.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["media_id"], ["media_files.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("checkin_id", "kind", name="uq_courier_checkin_photo_kind"),
    )
    op.create_index(op.f("ix_courier_daily_checkin_photos_checkin_id"), "courier_daily_checkin_photos", ["checkin_id"])
    op.create_index(op.f("ix_courier_daily_checkin_photos_media_id"), "courier_daily_checkin_photos", ["media_id"])

    # courier_delivery_tasks
    op.create_table(
        "courier_delivery_tasks",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("item_point_id", sa.Integer(), nullable=False),
        sa.Column("courier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="assigned"),
        sa.Column("taken_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("in_transit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("qr_scanned", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("delivery_photo_media_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("media_owner_uuid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["courier_id"], ["courier_accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["delivery_photo_media_id"], ["media_files.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["item_point_id"], ["delivery_order_item_points.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_courier_delivery_tasks_id"), "courier_delivery_tasks", ["id"])
    op.create_index(op.f("ix_courier_delivery_tasks_item_point_id"), "courier_delivery_tasks", ["item_point_id"])
    op.create_index(op.f("ix_courier_delivery_tasks_courier_id"), "courier_delivery_tasks", ["courier_id"])
    op.create_index(op.f("ix_courier_delivery_tasks_status"), "courier_delivery_tasks", ["status"])
    op.create_index(op.f("ix_courier_delivery_tasks_delivery_photo_media_id"), "courier_delivery_tasks", ["delivery_photo_media_id"])
    op.create_index(op.f("ix_courier_delivery_tasks_media_owner_uuid"), "courier_delivery_tasks", ["media_owner_uuid"])


def downgrade() -> None:
    op.drop_table("courier_delivery_tasks")
    op.drop_table("courier_daily_checkin_photos")
    op.drop_table("courier_daily_checkins")
    op.drop_table("courier_applications")
    op.drop_table("courier_vehicles")
    op.drop_table("courier_otp_codes")
    op.drop_table("courier_accounts")
