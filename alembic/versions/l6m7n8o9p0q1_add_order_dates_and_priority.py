"""Add order dates and priority

Revision ID: l6m7n8o9p0q1
Revises: k5l6m7n8o9p0
Create Date: 2026-01-23 15:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = 'l6m7n8o9p0q1'
down_revision: Union[str, None] = 'k5l6m7n8o9p0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new fields to delivery_orders."""
    op.execute("CREATE TYPE orderpriority AS ENUM ('normal', 'high', 'urgent')")
    
    op.add_column('delivery_orders',
                  sa.Column('priority', sa.Enum('normal', 'high', 'urgent', name='orderpriority'),
                           nullable=False, server_default='normal'))
    
    op.add_column('delivery_orders',
                  sa.Column('expected_pickup_date', sa.DateTime(), nullable=True))
    
    op.add_column('delivery_orders',
                  sa.Column('actual_pickup_date', sa.DateTime(), nullable=True))
    
    op.add_column('delivery_orders',
                  sa.Column('delivery_deadline', sa.DateTime(), nullable=True))
    
    op.execute("ALTER TYPE orderstatus ADD VALUE 'draft' BEFORE 'pending'")


def downgrade() -> None:
    """Remove new fields from delivery_orders."""
    op.drop_column('delivery_orders', 'delivery_deadline')
    op.drop_column('delivery_orders', 'actual_pickup_date')
    op.drop_column('delivery_orders', 'expected_pickup_date')
    op.drop_column('delivery_orders', 'priority')
    
    op.execute("DROP TYPE orderpriority")
    

