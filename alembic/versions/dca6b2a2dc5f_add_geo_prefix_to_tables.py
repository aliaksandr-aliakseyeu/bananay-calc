"""add_geo_prefix_to_tables

Revision ID: dca6b2a2dc5f
Revises: 109cbe768b76
Create Date: 2025-12-09 11:48:18.098438

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'dca6b2a2dc5f'
down_revision: Union[str, Sequence[str], None] = '109cbe768b76'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename tables to add geo_ prefix."""

    op.rename_table('product_categories', 'geo_product_categories')
    op.rename_table('tags', 'geo_tags')

    op.rename_table('countries', 'geo_countries')

    op.rename_table('regions', 'geo_regions')

    op.rename_table('sectors', 'geo_sectors')
    op.rename_table('distribution_centers', 'geo_distribution_centers')
    op.rename_table('region_pricing', 'geo_region_pricing')
    op.rename_table('settlements', 'geo_settlements')

    op.rename_table('districts', 'geo_districts')

    op.rename_table('categories', 'geo_categories')
    op.rename_table('subcategories', 'geo_subcategories')

    op.rename_table('delivery_points', 'geo_delivery_points')
    op.rename_table('delivery_point_tags', 'geo_delivery_point_tags')


def downgrade() -> None:
    """Remove geo_ prefix from tables."""
    op.rename_table('geo_delivery_point_tags', 'delivery_point_tags')
    op.rename_table('geo_delivery_points', 'delivery_points')

    op.rename_table('geo_subcategories', 'subcategories')
    op.rename_table('geo_categories', 'categories')

    op.rename_table('geo_districts', 'districts')

    op.rename_table('geo_settlements', 'settlements')
    op.rename_table('geo_region_pricing', 'region_pricing')
    op.rename_table('geo_distribution_centers', 'distribution_centers')
    op.rename_table('geo_sectors', 'sectors')

    op.rename_table('geo_regions', 'regions')

    op.rename_table('geo_countries', 'countries')

    op.rename_table('geo_tags', 'tags')
    op.rename_table('geo_product_categories', 'product_categories')
