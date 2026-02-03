"""add_producer_sku_logistics_fields

Revision ID: d48375456747
Revises: n8o9p0q1r2s3
Create Date: 2026-02-03 12:05:25.644489

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd48375456747'
down_revision: Union[str, Sequence[str], None] = 'n8o9p0q1r2s3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add basic product info fields
    op.add_column('producer_skus', sa.Column('barcode', sa.String(length=100), nullable=True, comment='Product barcode'))
    op.add_column('producer_skus', sa.Column('sales_channel', sa.String(length=50), nullable=True, comment='Sales channel: retail/horeca'))

    # Add transport box characteristics
    op.add_column('producer_skus', sa.Column('box_length_cm', sa.Numeric(precision=10, scale=2), nullable=True, comment='Transport box length in cm'))
    op.add_column('producer_skus', sa.Column('box_width_cm', sa.Numeric(precision=10, scale=2), nullable=True, comment='Transport box width in cm'))
    op.add_column('producer_skus', sa.Column('box_height_cm', sa.Numeric(precision=10, scale=2), nullable=True, comment='Transport box height in cm'))
    op.add_column('producer_skus', sa.Column('box_weight_g', sa.Numeric(precision=10, scale=2), nullable=True, comment='Transport box weight in grams'))

    # Add pallet characteristics
    op.add_column('producer_skus', sa.Column('items_per_pallet', sa.Integer(), nullable=True, comment='Number of items on euro pallet'))
    op.add_column('producer_skus', sa.Column('items_per_pallet_row', sa.Integer(), nullable=True, comment='Number of items in one pallet row'))
    op.add_column('producer_skus', sa.Column('max_pallet_rows', sa.Integer(), nullable=True, comment='Maximum number of rows on pallet'))
    op.add_column('producer_skus', sa.Column('pallet_height_cm', sa.Numeric(precision=10, scale=2), nullable=True, comment='Pallet height including pallet base in cm'))
    op.add_column('producer_skus', sa.Column('full_pallet_weight_kg', sa.Numeric(precision=10, scale=2), nullable=True, comment='Full pallet weight in kg'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove pallet characteristics
    op.drop_column('producer_skus', 'full_pallet_weight_kg')
    op.drop_column('producer_skus', 'pallet_height_cm')
    op.drop_column('producer_skus', 'max_pallet_rows')
    op.drop_column('producer_skus', 'items_per_pallet_row')
    op.drop_column('producer_skus', 'items_per_pallet')

    # Remove transport box characteristics
    op.drop_column('producer_skus', 'box_weight_g')
    op.drop_column('producer_skus', 'box_height_cm')
    op.drop_column('producer_skus', 'box_width_cm')
    op.drop_column('producer_skus', 'box_length_cm')

    # Remove basic product info fields
    op.drop_column('producer_skus', 'sales_channel')
    op.drop_column('producer_skus', 'barcode')
