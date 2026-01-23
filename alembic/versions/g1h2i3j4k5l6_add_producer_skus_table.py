"""add producer skus table

Revision ID: g1h2i3j4k5l6
Revises: a1b2c3d4e5f7
Create Date: 2026-01-20 15:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'g1h2i3j4k5l6'
down_revision: Union[str, Sequence[str], None] = 'h2i3j4k5l6m7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    op.create_table(
        'producer_skus',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('producer_id', sa.Integer(), nullable=False, comment='Producer (user) ID'),
        sa.Column('name', sa.String(length=200), nullable=False, comment='SKU name'),
        sa.Column('sku_code', sa.String(length=100), nullable=True, comment='SKU code/articul (unique per producer)'),
        sa.Column('description', sa.Text(), nullable=True, comment='SKU description'),
        sa.Column('length_cm', sa.Numeric(precision=10, scale=2), nullable=False, comment='Product length in cm'),
        sa.Column('width_cm', sa.Numeric(precision=10, scale=2), nullable=False, comment='Product width in cm'),
        sa.Column('height_cm', sa.Numeric(precision=10, scale=2), nullable=False, comment='Product height in cm'),
        sa.Column('weight_kg', sa.Numeric(precision=10, scale=3), nullable=False, comment='Weight of one item in kg'),
        sa.Column('items_per_box', sa.Integer(), nullable=False, comment="Number of items in producer's box"),
        sa.Column('product_category_id', sa.Integer(), nullable=True, comment='Product category ID'),
        sa.Column('temperature_mode_id', sa.Integer(), nullable=True, comment='Temperature mode ID'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='Is SKU active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Last update timestamp'),
        sa.ForeignKeyConstraint(['producer_id'], ['geo_users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_category_id'], ['geo_product_categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['temperature_mode_id'], ['geo_temperature_modes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_producer_skus_id', 'producer_skus', ['id'])
    op.create_index('ix_producer_skus_producer_id', 'producer_skus', ['producer_id'])
    op.create_index('ix_producer_skus_name', 'producer_skus', ['name'])
    op.create_index('ix_producer_skus_is_active', 'producer_skus', ['is_active'])
    op.create_index('ix_producer_skus_product_category_id', 'producer_skus', ['product_category_id'])
    op.create_index('ix_producer_skus_temperature_mode_id', 'producer_skus', ['temperature_mode_id'])
    
    # Create partial unique index for sku_code (only for non-NULL values)
    op.execute("""
        CREATE UNIQUE INDEX uq_producer_skus_sku_code_not_null 
        ON producer_skus (producer_id, sku_code) 
        WHERE sku_code IS NOT NULL
    """)


def downgrade() -> None:
    """Downgrade schema."""
    
    op.execute("DROP INDEX IF EXISTS uq_producer_skus_sku_code_not_null")
    op.drop_index('ix_producer_skus_temperature_mode_id', 'producer_skus')
    op.drop_index('ix_producer_skus_product_category_id', 'producer_skus')
    op.drop_index('ix_producer_skus_is_active', 'producer_skus')
    op.drop_index('ix_producer_skus_name', 'producer_skus')
    op.drop_index('ix_producer_skus_producer_id', 'producer_skus')
    op.drop_index('ix_producer_skus_id', 'producer_skus')
    op.drop_table('producer_skus')

