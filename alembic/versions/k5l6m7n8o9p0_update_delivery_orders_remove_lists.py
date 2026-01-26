"""Update delivery orders - remove lists dependency

Revision ID: k5l6m7n8o9p0
Revises: j4k5l6m7n8o9
Create Date: 2026-01-23 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'k5l6m7n8o9p0'
down_revision: Union[str, None] = 'j4k5l6m7n8o9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update delivery orders to store points directly without lists."""
    # Drop foreign key constraints first
    op.drop_constraint('delivery_orders_delivery_list_id_fkey', 'delivery_orders', type_='foreignkey')
    op.drop_constraint('delivery_order_points_delivery_list_item_id_fkey', 'delivery_order_points', type_='foreignkey')
    
    # Drop delivery_list_id column from delivery_orders
    op.drop_column('delivery_orders', 'delivery_list_id')
    
    # Rename delivery_list_item_id to delivery_point_id in delivery_order_points
    op.alter_column('delivery_order_points', 'delivery_list_item_id',
                    new_column_name='delivery_point_id',
                    existing_type=sa.Integer(),
                    existing_nullable=False)
    
    # Add new foreign key to delivery_points with RESTRICT on delete
    op.create_foreign_key(
        'delivery_order_points_delivery_point_id_fkey',
        'delivery_order_points',
        'geo_delivery_points',
        ['delivery_point_id'],
        ['id'],
        ondelete='RESTRICT'
    )


def downgrade() -> None:
    """Restore delivery orders to use lists."""
    # Drop new foreign key
    op.drop_constraint('delivery_order_points_delivery_point_id_fkey', 'delivery_order_points', type_='foreignkey')
    
    # Rename delivery_point_id back to delivery_list_item_id
    op.alter_column('delivery_order_points', 'delivery_point_id',
                    new_column_name='delivery_list_item_id',
                    existing_type=sa.Integer(),
                    existing_nullable=False)
    
    # Add delivery_list_id column back to delivery_orders (nullable for existing records)
    op.add_column('delivery_orders',
                  sa.Column('delivery_list_id', sa.Integer(), nullable=True))
    
    # Add foreign key constraints
    op.create_foreign_key(
        'delivery_order_points_delivery_list_item_id_fkey',
        'delivery_order_points',
        'geo_delivery_list_items',
        ['delivery_list_item_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'delivery_orders_delivery_list_id_fkey',
        'delivery_orders',
        'geo_delivery_lists',
        ['delivery_list_id'],
        ['id'],
        ondelete='CASCADE'
    )

