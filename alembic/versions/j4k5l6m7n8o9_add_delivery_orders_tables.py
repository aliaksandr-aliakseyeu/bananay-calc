"""Add delivery orders tables

Revision ID: j4k5l6m7n8o9
Revises: i3j4k5l6m7n8
Create Date: 2026-01-23 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = 'j4k5l6m7n8o9'
down_revision: Union[str, None] = 'i3j4k5l6m7n8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create delivery orders tables."""
    op.create_table(
        'delivery_orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_number', sa.String(length=50), nullable=False),
        sa.Column('producer_id', sa.Integer(), nullable=False),
        sa.Column('producer_sku_id', sa.Integer(), nullable=False),
        sa.Column('delivery_list_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('total_cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('cost_per_unit', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('status', sa.Enum(
            'pending',
            'in_transit_to_dc',
            'at_dc',
            'driver_assigned',
            'in_delivery',
            'partially_delivered',
            'completed',
            'cancelled',
            name='orderstatus',
            create_type=True
        ), nullable=False),
        sa.Column('producer_notes', sa.Text(), nullable=True),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('sent_to_dc_at', sa.DateTime(), nullable=True),
        sa.Column('arrived_at_dc_at', sa.DateTime(), nullable=True),
        sa.Column('driver_assigned_at', sa.DateTime(), nullable=True),
        sa.Column('delivery_started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['delivery_list_id'], ['geo_delivery_lists.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['producer_id'], ['geo_users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['producer_sku_id'], ['producer_skus.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_delivery_orders_id'), 'delivery_orders', ['id'], unique=False)
    op.create_index(op.f('ix_delivery_orders_order_number'), 'delivery_orders', ['order_number'], unique=True)

    op.create_table(
        'delivery_order_points',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('delivery_list_item_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum(
            'pending',
            'in_transit',
            'delivered',
            'failed',
            name='deliverypointstatus',
            create_type=True
        ), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('photo_url', sa.String(length=500), nullable=True),
        sa.Column('delivery_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['delivery_list_item_id'], ['geo_delivery_list_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['order_id'], ['delivery_orders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_delivery_order_points_id'), 'delivery_order_points', ['id'], unique=False)

    op.create_table(
        'delivery_order_status_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('changed_by_user_id', sa.Integer(), nullable=True),
        sa.Column('old_status', sa.Enum(
            'pending',
            'in_transit_to_dc',
            'at_dc',
            'driver_assigned',
            'in_delivery',
            'partially_delivered',
            'completed',
            'cancelled',
            name='orderstatus',
            create_type=False
        ), nullable=True),
        sa.Column('new_status', sa.Enum(
            'pending',
            'in_transit_to_dc',
            'at_dc',
            'driver_assigned',
            'in_delivery',
            'partially_delivered',
            'completed',
            'cancelled',
            name='orderstatus',
            create_type=False
        ), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['changed_by_user_id'], ['geo_users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['order_id'], ['delivery_orders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_delivery_order_status_history_id'), 'delivery_order_status_history', ['id'], unique=False)
    op.create_index(op.f('ix_delivery_order_status_history_created_at'), 'delivery_order_status_history', ['created_at'], unique=False)


def downgrade() -> None:
    """Drop delivery orders tables."""
    op.drop_index(op.f('ix_delivery_order_status_history_created_at'), table_name='delivery_order_status_history')
    op.drop_index(op.f('ix_delivery_order_status_history_id'), table_name='delivery_order_status_history')
    op.drop_table('delivery_order_status_history')
    
    op.drop_index(op.f('ix_delivery_order_points_id'), table_name='delivery_order_points')
    op.drop_table('delivery_order_points')
    
    op.drop_index(op.f('ix_delivery_orders_order_number'), table_name='delivery_orders')
    op.drop_index(op.f('ix_delivery_orders_id'), table_name='delivery_orders')
    op.drop_table('delivery_orders')
    
    sa.Enum(name='deliverypointstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='orderstatus').drop(op.get_bind(), checkfirst=True)

