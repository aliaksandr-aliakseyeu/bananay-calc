"""Fix delivery orders timestamps and enums

Revision ID: m7n8o9p0q1r2
Revises: l6m7n8o9p0q1
Create Date: 2026-01-23 16:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = 'm7n8o9p0q1r2'
down_revision: Union[str, None] = 'l6m7n8o9p0q1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix timestamps and add missing enum values."""
    
    op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'draft'")
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE orderpriority AS ENUM ('normal', 'high', 'urgent');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        ALTER TABLE delivery_orders
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE,
        ALTER COLUMN created_at SET DEFAULT NOW(),
        ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE,
        ALTER COLUMN updated_at SET DEFAULT NOW(),
        ALTER COLUMN expected_pickup_date TYPE TIMESTAMP WITH TIME ZONE,
        ALTER COLUMN actual_pickup_date TYPE TIMESTAMP WITH TIME ZONE,
        ALTER COLUMN delivery_deadline TYPE TIMESTAMP WITH TIME ZONE,
        ALTER COLUMN sent_to_dc_at TYPE TIMESTAMP WITH TIME ZONE,
        ALTER COLUMN arrived_at_dc_at TYPE TIMESTAMP WITH TIME ZONE,
        ALTER COLUMN driver_assigned_at TYPE TIMESTAMP WITH TIME ZONE,
        ALTER COLUMN delivery_started_at TYPE TIMESTAMP WITH TIME ZONE,
        ALTER COLUMN completed_at TYPE TIMESTAMP WITH TIME ZONE
    """)
    
    op.execute("""
        ALTER TABLE delivery_order_points
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE,
        ALTER COLUMN created_at SET DEFAULT NOW(),
        ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE,
        ALTER COLUMN updated_at SET DEFAULT NOW(),
        ALTER COLUMN delivered_at TYPE TIMESTAMP WITH TIME ZONE
    """)
    
    op.execute("""
        ALTER TABLE delivery_order_status_history
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE,
        ALTER COLUMN created_at SET DEFAULT NOW()
    """)


def downgrade() -> None:
    """Revert timestamp and enum changes."""
    
    op.execute("""
        ALTER TABLE delivery_orders
        ALTER COLUMN created_at DROP DEFAULT,
        ALTER COLUMN updated_at DROP DEFAULT,
        ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE,
        ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE,
        ALTER COLUMN expected_pickup_date TYPE TIMESTAMP WITHOUT TIME ZONE,
        ALTER COLUMN actual_pickup_date TYPE TIMESTAMP WITHOUT TIME ZONE,
        ALTER COLUMN delivery_deadline TYPE TIMESTAMP WITHOUT TIME ZONE,
        ALTER COLUMN sent_to_dc_at TYPE TIMESTAMP WITHOUT TIME ZONE,
        ALTER COLUMN arrived_at_dc_at TYPE TIMESTAMP WITHOUT TIME ZONE,
        ALTER COLUMN driver_assigned_at TYPE TIMESTAMP WITHOUT TIME ZONE,
        ALTER COLUMN delivery_started_at TYPE TIMESTAMP WITHOUT TIME ZONE,
        ALTER COLUMN completed_at TYPE TIMESTAMP WITHOUT TIME ZONE
    """)
    
    op.execute("""
        ALTER TABLE delivery_order_points
        ALTER COLUMN created_at DROP DEFAULT,
        ALTER COLUMN updated_at DROP DEFAULT,
        ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE,
        ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE,
        ALTER COLUMN delivered_at TYPE TIMESTAMP WITHOUT TIME ZONE
    """)
    
    op.execute("""
        ALTER TABLE delivery_order_status_history
        ALTER COLUMN created_at DROP DEFAULT,
        ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE
    """)
    


