"""add_daily_checkin_tables

Revision ID: 03549ea0f98d
Revises: v6w7x8y9z0a1
Create Date: 2026-02-12 12:29:34.746446

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '03549ea0f98d'
down_revision: Union[str, Sequence[str], None] = 'v6w7x8y9z0a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('daily_checkins',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('driver_id', sa.UUID(), nullable=False),
    sa.Column('vehicle_id', sa.UUID(), nullable=False),
    sa.Column('check_date', sa.Date(), nullable=False),
    sa.Column('status', sa.Enum('pending', 'completed', 'expired', name='dailycheckinstatus', native_enum=False, length=50), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('latitude', sa.Float(), nullable=True),
    sa.Column('longitude', sa.Float(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['driver_id'], ['driver_accounts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['vehicle_id'], ['driver_vehicles.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('driver_id', 'vehicle_id', 'check_date', name='uq_daily_checkin_driver_vehicle_date')
    )
    op.create_index(op.f('ix_daily_checkins_check_date'), 'daily_checkins', ['check_date'], unique=False)
    op.create_index('ix_daily_checkins_driver_date', 'daily_checkins', ['driver_id', 'check_date'], unique=False)
    op.create_index(op.f('ix_daily_checkins_driver_id'), 'daily_checkins', ['driver_id'], unique=False)
    op.create_index('ix_daily_checkins_status', 'daily_checkins', ['status'], unique=False)
    op.create_index(op.f('ix_daily_checkins_vehicle_id'), 'daily_checkins', ['vehicle_id'], unique=False)
    op.create_table('daily_checkin_photos',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('checkin_id', sa.UUID(), nullable=False),
    sa.Column('kind', sa.Enum('selfie', 'vehicle_front', 'vehicle_left', 'vehicle_right', 'vehicle_rear', 'vehicle_cargo', name='dailycheckinphotokind', native_enum=False, length=50), nullable=False),
    sa.Column('media_id', sa.UUID(), nullable=False),
    sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['checkin_id'], ['daily_checkins.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['media_id'], ['media_files.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('checkin_id', 'kind', name='uq_checkin_photo_kind')
    )
    op.create_index(op.f('ix_daily_checkin_photos_checkin_id'), 'daily_checkin_photos', ['checkin_id'], unique=False)
    op.create_index(op.f('ix_daily_checkin_photos_media_id'), 'daily_checkin_photos', ['media_id'], unique=False)
    op.alter_column('driver_accounts', 'status',
               existing_type=postgresql.ENUM('draft', 'pending_review', 'active', 'blocked', name='driveraccountstatus'),
               type_=sa.Enum('draft', 'pending_review', 'active', 'blocked', name='driveraccountstatus', native_enum=False, length=50),
               existing_nullable=False,
               existing_server_default=sa.text("'draft'::driveraccountstatus"))
    op.drop_index(op.f('ix_driver_accounts_city_id'), table_name='driver_accounts')
    op.drop_index(op.f('ix_driver_accounts_id'), table_name='driver_accounts')
    op.create_index(op.f('ix_driver_accounts_region_id'), 'driver_accounts', ['region_id'], unique=False)
    op.alter_column('driver_applications', 'status',
               existing_type=postgresql.ENUM('draft', 'pending_review', 'approved', 'rejected', name='driverapplicationstatus'),
               type_=sa.Enum('draft', 'pending_review', 'approved', 'rejected', name='driverapplicationstatus', native_enum=False, length=50),
               existing_nullable=False,
               existing_server_default=sa.text("'draft'::driverapplicationstatus"))
    op.drop_index(op.f('ix_driver_applications_id'), table_name='driver_applications')
    op.alter_column('driver_otp_codes', 'status',
               existing_type=postgresql.ENUM('pending', 'used', name='driverotpstatus'),
               type_=sa.Enum('pending', 'used', name='driverotpstatus', native_enum=False, length=20),
               existing_nullable=False,
               existing_server_default=sa.text("'pending'::driverotpstatus"))
    op.drop_index(op.f('ix_driver_telegram_bindings_telegram_chat_id'), table_name='driver_telegram_bindings')
    op.create_unique_constraint(None, 'driver_telegram_bindings', ['telegram_chat_id'])
    op.drop_index(op.f('ix_driver_vehicles_id'), table_name='driver_vehicles')
    op.drop_constraint(op.f('geo_delivery_point_suggestion_tags_tag_id_fkey'), 'geo_delivery_point_suggestion_tags', type_='foreignkey')
    op.create_foreign_key(None, 'geo_delivery_point_suggestion_tags', 'geo_tags', ['tag_id'], ['id'])
    op.alter_column('geo_delivery_point_suggestions', 'phone',
               existing_type=sa.TEXT(),
               comment='May contain multiple phone numbers separated by comma',
               existing_nullable=True)
    op.alter_column('geo_delivery_point_suggestions', 'mobile',
               existing_type=sa.TEXT(),
               comment='May contain multiple mobile numbers separated by comma',
               existing_nullable=True)
    op.alter_column('geo_delivery_point_suggestions', 'email',
               existing_type=sa.TEXT(),
               comment='May contain multiple emails separated by comma',
               existing_nullable=True)
    op.drop_constraint(op.f('geo_delivery_point_suggestions_created_by_id_fkey'), 'geo_delivery_point_suggestions', type_='foreignkey')
    op.drop_constraint(op.f('geo_delivery_point_suggestions_settlement_id_fkey'), 'geo_delivery_point_suggestions', type_='foreignkey')
    op.drop_constraint(op.f('geo_delivery_point_suggestions_category_id_fkey'), 'geo_delivery_point_suggestions', type_='foreignkey')
    op.drop_constraint(op.f('geo_delivery_point_suggestions_subcategory_id_fkey'), 'geo_delivery_point_suggestions', type_='foreignkey')
    op.drop_constraint(op.f('geo_delivery_point_suggestions_district_id_fkey'), 'geo_delivery_point_suggestions', type_='foreignkey')
    op.create_foreign_key(None, 'geo_delivery_point_suggestions', 'geo_settlements', ['settlement_id'], ['id'])
    op.create_foreign_key(None, 'geo_delivery_point_suggestions', 'geo_categories', ['category_id'], ['id'])
    op.create_foreign_key(None, 'geo_delivery_point_suggestions', 'geo_subcategories', ['subcategory_id'], ['id'])
    op.create_foreign_key(None, 'geo_delivery_point_suggestions', 'geo_users', ['created_by_id'], ['id'])
    op.create_foreign_key(None, 'geo_delivery_point_suggestions', 'geo_districts', ['district_id'], ['id'])
    op.alter_column('media_files', 'owner_type',
               existing_type=postgresql.ENUM('driver', 'application', 'shift', 'route_step', 'vehicle', name='mediafileownertype'),
               type_=sa.Enum('driver', 'application', 'shift', 'route_step', 'vehicle', 'daily_checkin', name='mediafileownertype', native_enum=False, length=50),
               existing_nullable=False)
    op.drop_index(op.f('ix_media_files_id'), table_name='media_files')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_index(op.f('ix_media_files_id'), 'media_files', ['id'], unique=False)
    op.alter_column('media_files', 'owner_type',
               existing_type=sa.Enum('driver', 'application', 'shift', 'route_step', 'vehicle', 'daily_checkin', name='mediafileownertype', native_enum=False, length=50),
               type_=postgresql.ENUM('driver', 'application', 'shift', 'route_step', 'vehicle', name='mediafileownertype'),
               existing_nullable=False)
    op.drop_constraint(None, 'geo_delivery_point_suggestions', type_='foreignkey')
    op.drop_constraint(None, 'geo_delivery_point_suggestions', type_='foreignkey')
    op.drop_constraint(None, 'geo_delivery_point_suggestions', type_='foreignkey')
    op.drop_constraint(None, 'geo_delivery_point_suggestions', type_='foreignkey')
    op.drop_constraint(None, 'geo_delivery_point_suggestions', type_='foreignkey')
    op.create_foreign_key(op.f('geo_delivery_point_suggestions_district_id_fkey'), 'geo_delivery_point_suggestions', 'geo_districts', ['district_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key(op.f('geo_delivery_point_suggestions_subcategory_id_fkey'), 'geo_delivery_point_suggestions', 'geo_subcategories', ['subcategory_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key(op.f('geo_delivery_point_suggestions_category_id_fkey'), 'geo_delivery_point_suggestions', 'geo_categories', ['category_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key(op.f('geo_delivery_point_suggestions_settlement_id_fkey'), 'geo_delivery_point_suggestions', 'geo_settlements', ['settlement_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('geo_delivery_point_suggestions_created_by_id_fkey'), 'geo_delivery_point_suggestions', 'geo_users', ['created_by_id'], ['id'], ondelete='CASCADE')
    op.alter_column('geo_delivery_point_suggestions', 'email',
               existing_type=sa.TEXT(),
               comment=None,
               existing_comment='May contain multiple emails separated by comma',
               existing_nullable=True)
    op.alter_column('geo_delivery_point_suggestions', 'mobile',
               existing_type=sa.TEXT(),
               comment=None,
               existing_comment='May contain multiple mobile numbers separated by comma',
               existing_nullable=True)
    op.alter_column('geo_delivery_point_suggestions', 'phone',
               existing_type=sa.TEXT(),
               comment=None,
               existing_comment='May contain multiple phone numbers separated by comma',
               existing_nullable=True)
    op.drop_constraint(None, 'geo_delivery_point_suggestion_tags', type_='foreignkey')
    op.create_foreign_key(op.f('geo_delivery_point_suggestion_tags_tag_id_fkey'), 'geo_delivery_point_suggestion_tags', 'geo_tags', ['tag_id'], ['id'], ondelete='CASCADE')
    op.create_index(op.f('ix_driver_vehicles_id'), 'driver_vehicles', ['id'], unique=False)
    op.drop_constraint(None, 'driver_telegram_bindings', type_='unique')
    op.create_index(op.f('ix_driver_telegram_bindings_telegram_chat_id'), 'driver_telegram_bindings', ['telegram_chat_id'], unique=True)
    op.alter_column('driver_otp_codes', 'status',
               existing_type=sa.Enum('pending', 'used', name='driverotpstatus', native_enum=False, length=20),
               type_=postgresql.ENUM('pending', 'used', name='driverotpstatus'),
               existing_nullable=False,
               existing_server_default=sa.text("'pending'::driverotpstatus"))
    op.create_index(op.f('ix_driver_applications_id'), 'driver_applications', ['id'], unique=False)
    op.alter_column('driver_applications', 'status',
               existing_type=sa.Enum('draft', 'pending_review', 'approved', 'rejected', name='driverapplicationstatus', native_enum=False, length=50),
               type_=postgresql.ENUM('draft', 'pending_review', 'approved', 'rejected', name='driverapplicationstatus'),
               existing_nullable=False,
               existing_server_default=sa.text("'draft'::driverapplicationstatus"))
    op.drop_index(op.f('ix_driver_accounts_region_id'), table_name='driver_accounts')
    op.create_index(op.f('ix_driver_accounts_id'), 'driver_accounts', ['id'], unique=False)
    op.create_index(op.f('ix_driver_accounts_city_id'), 'driver_accounts', ['region_id'], unique=False)
    op.alter_column('driver_accounts', 'status',
               existing_type=sa.Enum('draft', 'pending_review', 'active', 'blocked', name='driveraccountstatus', native_enum=False, length=50),
               type_=postgresql.ENUM('draft', 'pending_review', 'active', 'blocked', name='driveraccountstatus'),
               existing_nullable=False,
               existing_server_default=sa.text("'draft'::driveraccountstatus"))
    op.drop_index(op.f('ix_daily_checkin_photos_media_id'), table_name='daily_checkin_photos')
    op.drop_index(op.f('ix_daily_checkin_photos_checkin_id'), table_name='daily_checkin_photos')
    op.drop_table('daily_checkin_photos')
    op.drop_index(op.f('ix_daily_checkins_vehicle_id'), table_name='daily_checkins')
    op.drop_index('ix_daily_checkins_status', table_name='daily_checkins')
    op.drop_index(op.f('ix_daily_checkins_driver_id'), table_name='daily_checkins')
    op.drop_index('ix_daily_checkins_driver_date', table_name='daily_checkins')
    op.drop_index(op.f('ix_daily_checkins_check_date'), table_name='daily_checkins')
    op.drop_table('daily_checkins')
