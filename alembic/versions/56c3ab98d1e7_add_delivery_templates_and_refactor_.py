"""Add delivery templates and refactor delivery orders

Revision ID: 56c3ab98d1e7
Revises: d48375456747
Create Date: 2026-02-05 11:09:32.038935

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision: str = '56c3ab98d1e7'
down_revision: Union[str, Sequence[str], None] = 'd48375456747'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    op.drop_index(op.f('ix_delivery_order_points_id'), table_name='delivery_order_points')
    op.drop_table('delivery_order_points')
    
    op.create_table('delivery_templates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('producer_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('producer_sku_id', sa.Integer(), nullable=False),
    sa.Column('region_id', sa.Integer(), nullable=False),
    sa.Column('warehouse_lat', sa.Float(), nullable=False),
    sa.Column('warehouse_lon', sa.Float(), nullable=False),
    sa.Column('total_quantity', sa.Integer(), nullable=False),
    sa.Column('estimated_cost', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('cost_per_unit', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('last_calculated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('usage_count', sa.Integer(), nullable=False),
    sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['producer_id'], ['geo_users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['producer_sku_id'], ['producer_skus.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['region_id'], ['geo_regions.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_delivery_templates_id'), 'delivery_templates', ['id'], unique=False)
    op.create_index(op.f('ix_delivery_templates_is_active'), 'delivery_templates', ['is_active'], unique=False)
    op.create_index(op.f('ix_delivery_templates_producer_id'), 'delivery_templates', ['producer_id'], unique=False)
    op.create_index(op.f('ix_delivery_templates_producer_sku_id'), 'delivery_templates', ['producer_sku_id'], unique=False)
    op.create_index(op.f('ix_delivery_templates_region_id'), 'delivery_templates', ['region_id'], unique=False)
    op.create_table('delivery_order_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.Integer(), nullable=False),
    sa.Column('template_id', sa.Integer(), nullable=True),
    sa.Column('template_name', sa.String(length=200), nullable=False),
    sa.Column('producer_sku_id', sa.Integer(), nullable=False),
    sa.Column('sku_snapshot', sa.JSON(), nullable=True),
    sa.Column('region_id', sa.Integer(), nullable=False),
    sa.Column('warehouse_lat', sa.Float(), nullable=False),
    sa.Column('warehouse_lon', sa.Float(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('item_cost', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('cost_per_unit', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['delivery_orders.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['producer_sku_id'], ['producer_skus.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['region_id'], ['geo_regions.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['template_id'], ['delivery_templates.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_delivery_order_items_id'), 'delivery_order_items', ['id'], unique=False)
    op.create_index(op.f('ix_delivery_order_items_order_id'), 'delivery_order_items', ['order_id'], unique=False)
    op.create_index(op.f('ix_delivery_order_items_producer_sku_id'), 'delivery_order_items', ['producer_sku_id'], unique=False)
    op.create_index(op.f('ix_delivery_order_items_region_id'), 'delivery_order_items', ['region_id'], unique=False)
    op.create_index(op.f('ix_delivery_order_items_template_id'), 'delivery_order_items', ['template_id'], unique=False)
    op.create_table('delivery_order_item_points',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('order_item_id', sa.Integer(), nullable=False),
    sa.Column('delivery_point_id', sa.Integer(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('delivery_notes', sa.Text(), nullable=True),
    sa.Column('status', postgresql.ENUM('pending', 'in_transit', 'delivered', 'failed', name='deliverypointstatus', create_type=False), nullable=False),
    sa.Column('photo_url', sa.String(length=500), nullable=True),
    sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['delivery_point_id'], ['geo_delivery_points.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['order_item_id'], ['delivery_order_items.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_delivery_order_item_points_delivery_point_id'), 'delivery_order_item_points', ['delivery_point_id'], unique=False)
    op.create_index(op.f('ix_delivery_order_item_points_id'), 'delivery_order_item_points', ['id'], unique=False)
    op.create_index(op.f('ix_delivery_order_item_points_order_item_id'), 'delivery_order_item_points', ['order_item_id'], unique=False)
    op.create_index(op.f('ix_delivery_order_item_points_status'), 'delivery_order_item_points', ['status'], unique=False)
    op.create_table('delivery_template_points',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('template_id', sa.Integer(), nullable=False),
    sa.Column('delivery_point_id', sa.Integer(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['delivery_point_id'], ['geo_delivery_points.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['template_id'], ['delivery_templates.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_delivery_template_points_delivery_point_id'), 'delivery_template_points', ['delivery_point_id'], unique=False)
    op.create_index(op.f('ix_delivery_template_points_id'), 'delivery_template_points', ['id'], unique=False)
    op.create_index(op.f('ix_delivery_template_points_template_id'), 'delivery_template_points', ['template_id'], unique=False)
    
    op.create_index(op.f('ix_delivery_order_status_history_order_id'), 'delivery_order_status_history', ['order_id'], unique=False)
    op.add_column('delivery_orders', sa.Column('total_quantity', sa.Integer(), nullable=False, server_default='0'))
    op.create_index(op.f('ix_delivery_orders_producer_id'), 'delivery_orders', ['producer_id'], unique=False)
    op.create_index(op.f('ix_delivery_orders_status'), 'delivery_orders', ['status'], unique=False)
    op.drop_constraint(op.f('delivery_orders_producer_sku_id_fkey'), 'delivery_orders', type_='foreignkey')
    op.drop_column('delivery_orders', 'quantity')
    op.drop_column('delivery_orders', 'cost_per_unit')
    op.drop_column('delivery_orders', 'producer_sku_id')
    op.drop_index(op.f('ix_categories_id'), table_name='geo_categories')
    op.drop_index(op.f('ix_categories_name'), table_name='geo_categories')
    op.drop_index(op.f('ix_categories_slug'), table_name='geo_categories')
    op.create_index(op.f('ix_geo_categories_id'), 'geo_categories', ['id'], unique=False)
    op.create_index(op.f('ix_geo_categories_name'), 'geo_categories', ['name'], unique=True)
    op.create_index(op.f('ix_geo_categories_slug'), 'geo_categories', ['slug'], unique=True)
    op.alter_column('geo_countries', 'code',
               existing_type=sa.VARCHAR(length=2),
               comment='ISO country code',
               existing_comment='ISO код страны',
               existing_nullable=False)
    op.drop_index(op.f('ix_countries_id'), table_name='geo_countries')
    op.drop_index(op.f('ix_countries_name'), table_name='geo_countries')
    op.create_index(op.f('ix_geo_countries_id'), 'geo_countries', ['id'], unique=False)
    op.create_index(op.f('ix_geo_countries_name'), 'geo_countries', ['name'], unique=True)
    op.drop_constraint(op.f('uq_list_delivery_point'), 'geo_delivery_list_items', type_='unique')
    op.drop_constraint(op.f('uq_user_list_name'), 'geo_delivery_lists', type_='unique')
    op.alter_column('geo_delivery_points', 'name_normalized',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('geo_delivery_points', 'title',
               existing_type=sa.TEXT(),
               comment='Title (additional description)',
               existing_comment='Заголовок (дополнительное описание)',
               existing_nullable=True)
    op.alter_column('geo_delivery_points', 'phone',
               existing_type=sa.TEXT(),
               comment='May contain multiple phone numbers separated by comma',
               existing_comment='Может содержать несколько номеров через запятую',
               existing_nullable=True)
    op.alter_column('geo_delivery_points', 'mobile',
               existing_type=sa.TEXT(),
               comment='May contain multiple mobile numbers separated by comma',
               existing_comment='Может содержать несколько номеров через запятую',
               existing_nullable=True)
    op.alter_column('geo_delivery_points', 'email',
               existing_type=sa.TEXT(),
               comment='May contain multiple emails separated by comma',
               existing_comment='Может содержать несколько email через запятую',
               existing_nullable=True)
    op.drop_geospatial_index(op.f('idx_delivery_points_location'), table_name='geo_delivery_points', postgresql_using='gist', column_name='location')
    op.drop_index(op.f('idx_delivery_points_name_normalized_trgm'), table_name='geo_delivery_points', postgresql_ops={'name_normalized': 'gin_trgm_ops'}, postgresql_using='gin')
    op.drop_index(op.f('ix_delivery_points_category_id'), table_name='geo_delivery_points')
    op.drop_index(op.f('ix_delivery_points_district_id'), table_name='geo_delivery_points')
    op.drop_index(op.f('ix_delivery_points_id'), table_name='geo_delivery_points')
    op.drop_index(op.f('ix_delivery_points_name'), table_name='geo_delivery_points')
    op.drop_index(op.f('ix_delivery_points_settlement_id'), table_name='geo_delivery_points')
    op.drop_index(op.f('ix_delivery_points_subcategory_id'), table_name='geo_delivery_points')
    op.create_geospatial_index('idx_geo_delivery_points_location', 'geo_delivery_points', ['location'], unique=False, postgresql_using='gist', postgresql_ops={})
    op.create_index(op.f('ix_geo_delivery_points_category_id'), 'geo_delivery_points', ['category_id'], unique=False)
    op.create_index(op.f('ix_geo_delivery_points_district_id'), 'geo_delivery_points', ['district_id'], unique=False)
    op.create_index(op.f('ix_geo_delivery_points_id'), 'geo_delivery_points', ['id'], unique=False)
    op.create_index(op.f('ix_geo_delivery_points_name'), 'geo_delivery_points', ['name'], unique=False)
    op.create_index(op.f('ix_geo_delivery_points_name_normalized'), 'geo_delivery_points', ['name_normalized'], unique=False)
    op.create_index(op.f('ix_geo_delivery_points_settlement_id'), 'geo_delivery_points', ['settlement_id'], unique=False)
    op.create_index(op.f('ix_geo_delivery_points_subcategory_id'), 'geo_delivery_points', ['subcategory_id'], unique=False)
    op.drop_geospatial_index(op.f('idx_distribution_centers_location'), table_name='geo_distribution_centers', postgresql_using='gist', column_name='location')
    op.drop_index(op.f('ix_distribution_centers_id'), table_name='geo_distribution_centers')
    op.drop_index(op.f('ix_distribution_centers_name'), table_name='geo_distribution_centers')
    op.drop_index(op.f('ix_distribution_centers_region_id'), table_name='geo_distribution_centers')
    op.create_geospatial_index('idx_geo_distribution_centers_location', 'geo_distribution_centers', ['location'], unique=False, postgresql_using='gist', postgresql_ops={})
    op.create_index(op.f('ix_geo_distribution_centers_id'), 'geo_distribution_centers', ['id'], unique=False)
    op.create_index(op.f('ix_geo_distribution_centers_name'), 'geo_distribution_centers', ['name'], unique=False)
    op.create_index(op.f('ix_geo_distribution_centers_region_id'), 'geo_distribution_centers', ['region_id'], unique=False)
    op.drop_geospatial_index(op.f('idx_districts_boundary'), table_name='geo_districts', postgresql_using='gist', column_name='boundary')
    op.drop_index(op.f('ix_districts_id'), table_name='geo_districts')
    op.drop_index(op.f('ix_districts_name'), table_name='geo_districts')
    op.drop_index(op.f('ix_districts_settlement_id'), table_name='geo_districts')
    op.create_geospatial_index('idx_geo_districts_boundary', 'geo_districts', ['boundary'], unique=False, postgresql_using='gist', postgresql_ops={})
    op.create_index(op.f('ix_geo_districts_id'), 'geo_districts', ['id'], unique=False)
    op.create_index(op.f('ix_geo_districts_name'), 'geo_districts', ['name'], unique=False)
    op.create_index(op.f('ix_geo_districts_settlement_id'), 'geo_districts', ['settlement_id'], unique=False)
    op.drop_index(op.f('ix_product_categories_id'), table_name='geo_product_categories')
    op.drop_index(op.f('ix_product_categories_name'), table_name='geo_product_categories')
    op.drop_index(op.f('ix_product_categories_slug'), table_name='geo_product_categories')
    op.drop_constraint(op.f('uq_geo_product_categories_name'), 'geo_product_categories', type_='unique')
    op.drop_constraint(op.f('uq_geo_product_categories_slug'), 'geo_product_categories', type_='unique')
    op.create_index(op.f('ix_geo_product_categories_id'), 'geo_product_categories', ['id'], unique=False)
    op.create_index(op.f('ix_geo_product_categories_name'), 'geo_product_categories', ['name'], unique=True)
    op.create_index(op.f('ix_geo_product_categories_slug'), 'geo_product_categories', ['slug'], unique=True)
    op.alter_column('geo_region_pricing', 'driver_hourly_rate',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               comment='Driver hourly rate, RUB',
               existing_comment='Стоимость 1 часа работы водителя, руб.',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'planned_work_hours',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               comment='Planned working hours',
               existing_comment='Часов на выполнение работы по плану',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'fuel_price_per_liter',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               comment='Fuel price, RUB/L',
               existing_comment='Стоимость бензина, руб/л',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'fuel_consumption_per_100km',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               comment='Fuel consumption, L/100km',
               existing_comment='Расход бензина, л/100км',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'depreciation_coefficient',
               existing_type=sa.NUMERIC(precision=10, scale=4),
               comment='Vehicle depreciation coefficient',
               existing_comment='Коэффициент амортизации авто',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'warehouse_processing_per_kg',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               comment='Warehouse processing cost per kg, RUB',
               existing_comment='Стоимость обработки 1 кг на РЦ, руб.',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'service_fee_per_kg',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               comment='Service fee per kg (company revenue), RUB',
               existing_comment='Сервисный сбор 1 кг (выручка компании), руб.',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'delivery_point_cost',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               comment='Cost per delivery point, RUB',
               existing_comment='Стоимость одной точки доставки, руб.',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'standard_trip_weight',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               comment='Standard trip cargo weight, kg',
               existing_comment='Стандартный вес груза в рейсе, кг',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'standard_box_length',
               existing_type=sa.INTEGER(),
               comment='Standard box length, cm',
               existing_comment='Длина эталонной коробки, см',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'standard_box_width',
               existing_type=sa.INTEGER(),
               comment='Standard box width, cm',
               existing_comment='Ширина эталонной коробки, см',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'standard_box_height',
               existing_type=sa.INTEGER(),
               comment='Standard box height, cm',
               existing_comment='Высота эталонной коробки, см',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'standard_box_max_weight',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               comment='Standard box maximum weight, kg',
               existing_comment='Максимальный вес эталонной коробки, кг',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'min_points_for_discount',
               existing_type=sa.INTEGER(),
               comment='Minimum points before discount applies',
               existing_comment='Минимальное количество точек до применения скидки',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'discount_step_points',
               existing_type=sa.INTEGER(),
               comment='Step increment for delivery points',
               existing_comment='Шаг прироста количества точек доставки',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'initial_discount_percent',
               existing_type=sa.NUMERIC(precision=5, scale=2),
               comment='Initial discount, %',
               existing_comment='Стартовая скидка, %',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'discount_step_percent',
               existing_type=sa.NUMERIC(precision=5, scale=2),
               comment='Discount step increment, %',
               existing_comment='Шаг прироста скидки, %',
               existing_nullable=False)
    op.drop_index(op.f('ix_region_pricing_id'), table_name='geo_region_pricing')
    op.drop_index(op.f('ix_region_pricing_region_id'), table_name='geo_region_pricing')
    op.create_index(op.f('ix_geo_region_pricing_id'), 'geo_region_pricing', ['id'], unique=False)
    op.create_index(op.f('ix_geo_region_pricing_region_id'), 'geo_region_pricing', ['region_id'], unique=True)
    op.alter_column('geo_regions', 'type',
               existing_type=sa.VARCHAR(length=50),
               comment='Region type',
               existing_comment='Тип региона',
               existing_nullable=True)
    op.drop_index(op.f('ix_regions_country_id'), table_name='geo_regions')
    op.drop_index(op.f('ix_regions_id'), table_name='geo_regions')
    op.drop_index(op.f('ix_regions_name'), table_name='geo_regions')
    op.create_index(op.f('ix_geo_regions_country_id'), 'geo_regions', ['country_id'], unique=False)
    op.create_index(op.f('ix_geo_regions_id'), 'geo_regions', ['id'], unique=False)
    op.create_index(op.f('ix_geo_regions_name'), 'geo_regions', ['name'], unique=False)
    op.alter_column('geo_sectors', 'name',
               existing_type=sa.VARCHAR(length=200),
               comment='Sector name (optional, sectors are mainly used for calculations)',
               existing_comment='Название сектора (опционально, сектора используются в основном для расчетов)',
               existing_nullable=True)
    op.alter_column('geo_sectors', 'description',
               existing_type=sa.TEXT(),
               comment='Sector description',
               existing_comment='Описание сектора',
               existing_nullable=True)
    op.alter_column('geo_sectors', 'boundary',
               existing_type=Geometry(geometry_type='POLYGON', srid=4326, dimension=2, from_text='ST_GeomFromEWKT', name='geometry', nullable=False, _spatial_index_reflected=True),
               comment='Sector boundary (polygon)',
               existing_comment='Граница сектора (полигон)',
               existing_nullable=False)
    op.drop_geospatial_index(op.f('idx_sectors_boundary'), table_name='geo_sectors', postgresql_using='gist', column_name='boundary')
    op.drop_index(op.f('ix_sectors_id'), table_name='geo_sectors')
    op.drop_index(op.f('ix_sectors_name'), table_name='geo_sectors')
    op.drop_index(op.f('ix_sectors_region_id'), table_name='geo_sectors')
    op.create_geospatial_index('idx_geo_sectors_boundary', 'geo_sectors', ['boundary'], unique=False, postgresql_using='gist', postgresql_ops={})
    op.create_index(op.f('ix_geo_sectors_id'), 'geo_sectors', ['id'], unique=False)
    op.create_index(op.f('ix_geo_sectors_name'), 'geo_sectors', ['name'], unique=False)
    op.create_index(op.f('ix_geo_sectors_region_id'), 'geo_sectors', ['region_id'], unique=False)
    op.drop_geospatial_index(op.f('idx_settlements_location'), table_name='geo_settlements', postgresql_using='gist', column_name='location')
    op.drop_index(op.f('ix_settlements_id'), table_name='geo_settlements')
    op.drop_index(op.f('ix_settlements_name'), table_name='geo_settlements')
    op.drop_index(op.f('ix_settlements_region_id'), table_name='geo_settlements')
    op.create_geospatial_index('idx_geo_settlements_location', 'geo_settlements', ['location'], unique=False, postgresql_using='gist', postgresql_ops={})
    op.create_index(op.f('ix_geo_settlements_id'), 'geo_settlements', ['id'], unique=False)
    op.create_index(op.f('ix_geo_settlements_name'), 'geo_settlements', ['name'], unique=False)
    op.create_index(op.f('ix_geo_settlements_region_id'), 'geo_settlements', ['region_id'], unique=False)
    op.drop_index(op.f('ix_subcategories_category_id'), table_name='geo_subcategories')
    op.drop_index(op.f('ix_subcategories_id'), table_name='geo_subcategories')
    op.drop_index(op.f('ix_subcategories_name'), table_name='geo_subcategories')
    op.drop_index(op.f('ix_subcategories_slug'), table_name='geo_subcategories')
    op.create_index(op.f('ix_geo_subcategories_category_id'), 'geo_subcategories', ['category_id'], unique=False)
    op.create_index(op.f('ix_geo_subcategories_id'), 'geo_subcategories', ['id'], unique=False)
    op.create_index(op.f('ix_geo_subcategories_name'), 'geo_subcategories', ['name'], unique=False)
    op.create_index(op.f('ix_geo_subcategories_slug'), 'geo_subcategories', ['slug'], unique=False)
    op.drop_index(op.f('ix_tags_id'), table_name='geo_tags')
    op.drop_index(op.f('ix_tags_name'), table_name='geo_tags')
    op.drop_index(op.f('ix_tags_slug'), table_name='geo_tags')
    op.create_index(op.f('ix_geo_tags_id'), 'geo_tags', ['id'], unique=False)
    op.create_index(op.f('ix_geo_tags_name'), 'geo_tags', ['name'], unique=True)
    op.create_index(op.f('ix_geo_tags_slug'), 'geo_tags', ['slug'], unique=True)
    op.alter_column('geo_temperature_modes', 'name',
               existing_type=sa.VARCHAR(length=100),
               comment=None,
               existing_comment='Название температурного режима',
               existing_nullable=False)
    op.alter_column('geo_temperature_modes', 'description',
               existing_type=sa.TEXT(),
               comment=None,
               existing_comment='Описание режима',
               existing_nullable=True)
    op.alter_column('geo_temperature_modes', 'is_active',
               existing_type=sa.BOOLEAN(),
               comment=None,
               existing_comment='Активность режима',
               existing_nullable=False,
               existing_server_default=sa.text('true'))
    op.alter_column('geo_temperature_modes', 'slug',
               existing_type=sa.VARCHAR(length=100),
               comment=None,
               existing_comment='URL-friendly название',
               existing_nullable=False)
    op.drop_constraint(op.f('geo_temperature_modes_slug_key'), 'geo_temperature_modes', type_='unique')
    op.drop_constraint(op.f('producer_profiles_company_inn_key'), 'producer_profiles', type_='unique')
    op.drop_constraint(op.f('producer_profiles_user_id_key'), 'producer_profiles', type_='unique')
    op.drop_index(op.f('ix_producer_profiles_company_inn'), table_name='producer_profiles')
    op.create_index(op.f('ix_producer_profiles_company_inn'), 'producer_profiles', ['company_inn'], unique=True)
    op.drop_index(op.f('ix_producer_profiles_user_id'), table_name='producer_profiles')
    op.create_index(op.f('ix_producer_profiles_user_id'), 'producer_profiles', ['user_id'], unique=True)
    op.drop_index(op.f('uq_producer_skus_sku_code_not_null'), table_name='producer_skus', postgresql_where='(sku_code IS NOT NULL)')
    op.drop_constraint(op.f('uq_producer_tutorial_type'), 'producer_tutorials', type_='unique')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_unique_constraint(op.f('uq_producer_tutorial_type'), 'producer_tutorials', ['producer_id', 'tutorial_type'], postgresql_nulls_not_distinct=False)
    op.create_index(op.f('uq_producer_skus_sku_code_not_null'), 'producer_skus', ['producer_id', 'sku_code'], unique=True, postgresql_where='(sku_code IS NOT NULL)')
    op.drop_index(op.f('ix_producer_profiles_user_id'), table_name='producer_profiles')
    op.create_index(op.f('ix_producer_profiles_user_id'), 'producer_profiles', ['user_id'], unique=False)
    op.drop_index(op.f('ix_producer_profiles_company_inn'), table_name='producer_profiles')
    op.create_index(op.f('ix_producer_profiles_company_inn'), 'producer_profiles', ['company_inn'], unique=False)
    op.create_unique_constraint(op.f('producer_profiles_user_id_key'), 'producer_profiles', ['user_id'], postgresql_nulls_not_distinct=False)
    op.create_unique_constraint(op.f('producer_profiles_company_inn_key'), 'producer_profiles', ['company_inn'], postgresql_nulls_not_distinct=False)
    op.create_unique_constraint(op.f('geo_temperature_modes_slug_key'), 'geo_temperature_modes', ['slug'], postgresql_nulls_not_distinct=False)
    op.alter_column('geo_temperature_modes', 'slug',
               existing_type=sa.VARCHAR(length=100),
               comment='URL-friendly название',
               existing_nullable=False)
    op.alter_column('geo_temperature_modes', 'is_active',
               existing_type=sa.BOOLEAN(),
               comment='Активность режима',
               existing_nullable=False,
               existing_server_default=sa.text('true'))
    op.alter_column('geo_temperature_modes', 'description',
               existing_type=sa.TEXT(),
               comment='Описание режима',
               existing_nullable=True)
    op.alter_column('geo_temperature_modes', 'name',
               existing_type=sa.VARCHAR(length=100),
               comment='Название температурного режима',
               existing_nullable=False)
    op.drop_index(op.f('ix_geo_tags_slug'), table_name='geo_tags')
    op.drop_index(op.f('ix_geo_tags_name'), table_name='geo_tags')
    op.drop_index(op.f('ix_geo_tags_id'), table_name='geo_tags')
    op.create_index(op.f('ix_tags_slug'), 'geo_tags', ['slug'], unique=True)
    op.create_index(op.f('ix_tags_name'), 'geo_tags', ['name'], unique=True)
    op.create_index(op.f('ix_tags_id'), 'geo_tags', ['id'], unique=False)
    op.drop_index(op.f('ix_geo_subcategories_slug'), table_name='geo_subcategories')
    op.drop_index(op.f('ix_geo_subcategories_name'), table_name='geo_subcategories')
    op.drop_index(op.f('ix_geo_subcategories_id'), table_name='geo_subcategories')
    op.drop_index(op.f('ix_geo_subcategories_category_id'), table_name='geo_subcategories')
    op.create_index(op.f('ix_subcategories_slug'), 'geo_subcategories', ['slug'], unique=False)
    op.create_index(op.f('ix_subcategories_name'), 'geo_subcategories', ['name'], unique=False)
    op.create_index(op.f('ix_subcategories_id'), 'geo_subcategories', ['id'], unique=False)
    op.create_index(op.f('ix_subcategories_category_id'), 'geo_subcategories', ['category_id'], unique=False)
    op.drop_index(op.f('ix_geo_settlements_region_id'), table_name='geo_settlements')
    op.drop_index(op.f('ix_geo_settlements_name'), table_name='geo_settlements')
    op.drop_index(op.f('ix_geo_settlements_id'), table_name='geo_settlements')
    op.drop_geospatial_index('idx_geo_settlements_location', table_name='geo_settlements', postgresql_using='gist', column_name='location')
    op.create_index(op.f('ix_settlements_region_id'), 'geo_settlements', ['region_id'], unique=False)
    op.create_index(op.f('ix_settlements_name'), 'geo_settlements', ['name'], unique=False)
    op.create_index(op.f('ix_settlements_id'), 'geo_settlements', ['id'], unique=False)
    op.create_geospatial_index(op.f('idx_settlements_location'), 'geo_settlements', ['location'], unique=False, postgresql_using='gist', postgresql_ops={})
    op.drop_index(op.f('ix_geo_sectors_region_id'), table_name='geo_sectors')
    op.drop_index(op.f('ix_geo_sectors_name'), table_name='geo_sectors')
    op.drop_index(op.f('ix_geo_sectors_id'), table_name='geo_sectors')
    op.drop_geospatial_index('idx_geo_sectors_boundary', table_name='geo_sectors', postgresql_using='gist', column_name='boundary')
    op.create_index(op.f('ix_sectors_region_id'), 'geo_sectors', ['region_id'], unique=False)
    op.create_index(op.f('ix_sectors_name'), 'geo_sectors', ['name'], unique=False)
    op.create_index(op.f('ix_sectors_id'), 'geo_sectors', ['id'], unique=False)
    op.create_geospatial_index(op.f('idx_sectors_boundary'), 'geo_sectors', ['boundary'], unique=False, postgresql_using='gist', postgresql_ops={})
    op.alter_column('geo_sectors', 'boundary',
               existing_type=Geometry(geometry_type='POLYGON', srid=4326, dimension=2, from_text='ST_GeomFromEWKT', name='geometry', nullable=False, _spatial_index_reflected=True),
               comment='Граница сектора (полигон)',
               existing_comment='Sector boundary (polygon)',
               existing_nullable=False)
    op.alter_column('geo_sectors', 'description',
               existing_type=sa.TEXT(),
               comment='Описание сектора',
               existing_comment='Sector description',
               existing_nullable=True)
    op.alter_column('geo_sectors', 'name',
               existing_type=sa.VARCHAR(length=200),
               comment='Название сектора (опционально, сектора используются в основном для расчетов)',
               existing_comment='Sector name (optional, sectors are mainly used for calculations)',
               existing_nullable=True)
    op.drop_index(op.f('ix_geo_regions_name'), table_name='geo_regions')
    op.drop_index(op.f('ix_geo_regions_id'), table_name='geo_regions')
    op.drop_index(op.f('ix_geo_regions_country_id'), table_name='geo_regions')
    op.create_index(op.f('ix_regions_name'), 'geo_regions', ['name'], unique=False)
    op.create_index(op.f('ix_regions_id'), 'geo_regions', ['id'], unique=False)
    op.create_index(op.f('ix_regions_country_id'), 'geo_regions', ['country_id'], unique=False)
    op.alter_column('geo_regions', 'type',
               existing_type=sa.VARCHAR(length=50),
               comment='Тип региона',
               existing_comment='Region type',
               existing_nullable=True)
    op.drop_index(op.f('ix_geo_region_pricing_region_id'), table_name='geo_region_pricing')
    op.drop_index(op.f('ix_geo_region_pricing_id'), table_name='geo_region_pricing')
    op.create_index(op.f('ix_region_pricing_region_id'), 'geo_region_pricing', ['region_id'], unique=True)
    op.create_index(op.f('ix_region_pricing_id'), 'geo_region_pricing', ['id'], unique=False)
    op.alter_column('geo_region_pricing', 'discount_step_percent',
               existing_type=sa.NUMERIC(precision=5, scale=2),
               comment='Шаг прироста скидки, %',
               existing_comment='Discount step increment, %',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'initial_discount_percent',
               existing_type=sa.NUMERIC(precision=5, scale=2),
               comment='Стартовая скидка, %',
               existing_comment='Initial discount, %',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'discount_step_points',
               existing_type=sa.INTEGER(),
               comment='Шаг прироста количества точек доставки',
               existing_comment='Step increment for delivery points',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'min_points_for_discount',
               existing_type=sa.INTEGER(),
               comment='Минимальное количество точек до применения скидки',
               existing_comment='Minimum points before discount applies',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'standard_box_max_weight',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               comment='Максимальный вес эталонной коробки, кг',
               existing_comment='Standard box maximum weight, kg',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'standard_box_height',
               existing_type=sa.INTEGER(),
               comment='Высота эталонной коробки, см',
               existing_comment='Standard box height, cm',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'standard_box_width',
               existing_type=sa.INTEGER(),
               comment='Ширина эталонной коробки, см',
               existing_comment='Standard box width, cm',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'standard_box_length',
               existing_type=sa.INTEGER(),
               comment='Длина эталонной коробки, см',
               existing_comment='Standard box length, cm',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'standard_trip_weight',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               comment='Стандартный вес груза в рейсе, кг',
               existing_comment='Standard trip cargo weight, kg',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'delivery_point_cost',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               comment='Стоимость одной точки доставки, руб.',
               existing_comment='Cost per delivery point, RUB',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'service_fee_per_kg',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               comment='Сервисный сбор 1 кг (выручка компании), руб.',
               existing_comment='Service fee per kg (company revenue), RUB',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'warehouse_processing_per_kg',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               comment='Стоимость обработки 1 кг на РЦ, руб.',
               existing_comment='Warehouse processing cost per kg, RUB',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'depreciation_coefficient',
               existing_type=sa.NUMERIC(precision=10, scale=4),
               comment='Коэффициент амортизации авто',
               existing_comment='Vehicle depreciation coefficient',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'fuel_consumption_per_100km',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               comment='Расход бензина, л/100км',
               existing_comment='Fuel consumption, L/100km',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'fuel_price_per_liter',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               comment='Стоимость бензина, руб/л',
               existing_comment='Fuel price, RUB/L',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'planned_work_hours',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               comment='Часов на выполнение работы по плану',
               existing_comment='Planned working hours',
               existing_nullable=False)
    op.alter_column('geo_region_pricing', 'driver_hourly_rate',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               comment='Стоимость 1 часа работы водителя, руб.',
               existing_comment='Driver hourly rate, RUB',
               existing_nullable=False)
    op.drop_index(op.f('ix_geo_product_categories_slug'), table_name='geo_product_categories')
    op.drop_index(op.f('ix_geo_product_categories_name'), table_name='geo_product_categories')
    op.drop_index(op.f('ix_geo_product_categories_id'), table_name='geo_product_categories')
    op.create_unique_constraint(op.f('uq_geo_product_categories_slug'), 'geo_product_categories', ['slug'], postgresql_nulls_not_distinct=False)
    op.create_unique_constraint(op.f('uq_geo_product_categories_name'), 'geo_product_categories', ['name'], postgresql_nulls_not_distinct=False)
    op.create_index(op.f('ix_product_categories_slug'), 'geo_product_categories', ['slug'], unique=True)
    op.create_index(op.f('ix_product_categories_name'), 'geo_product_categories', ['name'], unique=True)
    op.create_index(op.f('ix_product_categories_id'), 'geo_product_categories', ['id'], unique=False)
    op.drop_index(op.f('ix_geo_districts_settlement_id'), table_name='geo_districts')
    op.drop_index(op.f('ix_geo_districts_name'), table_name='geo_districts')
    op.drop_index(op.f('ix_geo_districts_id'), table_name='geo_districts')
    op.drop_geospatial_index('idx_geo_districts_boundary', table_name='geo_districts', postgresql_using='gist', column_name='boundary')
    op.create_index(op.f('ix_districts_settlement_id'), 'geo_districts', ['settlement_id'], unique=False)
    op.create_index(op.f('ix_districts_name'), 'geo_districts', ['name'], unique=False)
    op.create_index(op.f('ix_districts_id'), 'geo_districts', ['id'], unique=False)
    op.create_geospatial_index(op.f('idx_districts_boundary'), 'geo_districts', ['boundary'], unique=False, postgresql_using='gist', postgresql_ops={})
    op.drop_index(op.f('ix_geo_distribution_centers_region_id'), table_name='geo_distribution_centers')
    op.drop_index(op.f('ix_geo_distribution_centers_name'), table_name='geo_distribution_centers')
    op.drop_index(op.f('ix_geo_distribution_centers_id'), table_name='geo_distribution_centers')
    op.drop_geospatial_index('idx_geo_distribution_centers_location', table_name='geo_distribution_centers', postgresql_using='gist', column_name='location')
    op.create_index(op.f('ix_distribution_centers_region_id'), 'geo_distribution_centers', ['region_id'], unique=False)
    op.create_index(op.f('ix_distribution_centers_name'), 'geo_distribution_centers', ['name'], unique=False)
    op.create_index(op.f('ix_distribution_centers_id'), 'geo_distribution_centers', ['id'], unique=False)
    op.create_geospatial_index(op.f('idx_distribution_centers_location'), 'geo_distribution_centers', ['location'], unique=False, postgresql_using='gist', postgresql_ops={})
    op.drop_index(op.f('ix_geo_delivery_points_subcategory_id'), table_name='geo_delivery_points')
    op.drop_index(op.f('ix_geo_delivery_points_settlement_id'), table_name='geo_delivery_points')
    op.drop_index(op.f('ix_geo_delivery_points_name_normalized'), table_name='geo_delivery_points')
    op.drop_index(op.f('ix_geo_delivery_points_name'), table_name='geo_delivery_points')
    op.drop_index(op.f('ix_geo_delivery_points_id'), table_name='geo_delivery_points')
    op.drop_index(op.f('ix_geo_delivery_points_district_id'), table_name='geo_delivery_points')
    op.drop_index(op.f('ix_geo_delivery_points_category_id'), table_name='geo_delivery_points')
    op.drop_geospatial_index('idx_geo_delivery_points_location', table_name='geo_delivery_points', postgresql_using='gist', column_name='location')
    op.create_index(op.f('ix_delivery_points_subcategory_id'), 'geo_delivery_points', ['subcategory_id'], unique=False)
    op.create_index(op.f('ix_delivery_points_settlement_id'), 'geo_delivery_points', ['settlement_id'], unique=False)
    op.create_index(op.f('ix_delivery_points_name'), 'geo_delivery_points', ['name'], unique=False)
    op.create_index(op.f('ix_delivery_points_id'), 'geo_delivery_points', ['id'], unique=False)
    op.create_index(op.f('ix_delivery_points_district_id'), 'geo_delivery_points', ['district_id'], unique=False)
    op.create_index(op.f('ix_delivery_points_category_id'), 'geo_delivery_points', ['category_id'], unique=False)
    op.create_index(op.f('idx_delivery_points_name_normalized_trgm'), 'geo_delivery_points', ['name_normalized'], unique=False, postgresql_ops={'name_normalized': 'gin_trgm_ops'}, postgresql_using='gin')
    op.create_geospatial_index(op.f('idx_delivery_points_location'), 'geo_delivery_points', ['location'], unique=False, postgresql_using='gist', postgresql_ops={})
    op.alter_column('geo_delivery_points', 'email',
               existing_type=sa.TEXT(),
               comment='Может содержать несколько email через запятую',
               existing_comment='May contain multiple emails separated by comma',
               existing_nullable=True)
    op.alter_column('geo_delivery_points', 'mobile',
               existing_type=sa.TEXT(),
               comment='Может содержать несколько номеров через запятую',
               existing_comment='May contain multiple mobile numbers separated by comma',
               existing_nullable=True)
    op.alter_column('geo_delivery_points', 'phone',
               existing_type=sa.TEXT(),
               comment='Может содержать несколько номеров через запятую',
               existing_comment='May contain multiple phone numbers separated by comma',
               existing_nullable=True)
    op.alter_column('geo_delivery_points', 'title',
               existing_type=sa.TEXT(),
               comment='Заголовок (дополнительное описание)',
               existing_comment='Title (additional description)',
               existing_nullable=True)
    op.alter_column('geo_delivery_points', 'name_normalized',
               existing_type=sa.TEXT(),
               nullable=True)
    op.create_unique_constraint(op.f('uq_user_list_name'), 'geo_delivery_lists', ['user_id', 'name'], postgresql_nulls_not_distinct=False)
    op.create_unique_constraint(op.f('uq_list_delivery_point'), 'geo_delivery_list_items', ['list_id', 'delivery_point_id'], postgresql_nulls_not_distinct=False)
    op.drop_index(op.f('ix_geo_countries_name'), table_name='geo_countries')
    op.drop_index(op.f('ix_geo_countries_id'), table_name='geo_countries')
    op.create_index(op.f('ix_countries_name'), 'geo_countries', ['name'], unique=True)
    op.create_index(op.f('ix_countries_id'), 'geo_countries', ['id'], unique=False)
    op.alter_column('geo_countries', 'code',
               existing_type=sa.VARCHAR(length=2),
               comment='ISO код страны',
               existing_comment='ISO country code',
               existing_nullable=False)
    op.drop_index(op.f('ix_geo_categories_slug'), table_name='geo_categories')
    op.drop_index(op.f('ix_geo_categories_name'), table_name='geo_categories')
    op.drop_index(op.f('ix_geo_categories_id'), table_name='geo_categories')
    op.create_index(op.f('ix_categories_slug'), 'geo_categories', ['slug'], unique=True)
    op.create_index(op.f('ix_categories_name'), 'geo_categories', ['name'], unique=True)
    op.create_index(op.f('ix_categories_id'), 'geo_categories', ['id'], unique=False)
    op.add_column('delivery_orders', sa.Column('producer_sku_id', sa.INTEGER(), autoincrement=False, nullable=False))
    op.add_column('delivery_orders', sa.Column('cost_per_unit', sa.NUMERIC(precision=10, scale=2), autoincrement=False, nullable=True))
    op.add_column('delivery_orders', sa.Column('quantity', sa.INTEGER(), autoincrement=False, nullable=False))
    op.create_foreign_key(op.f('delivery_orders_producer_sku_id_fkey'), 'delivery_orders', 'producer_skus', ['producer_sku_id'], ['id'], ondelete='RESTRICT')
    op.drop_index(op.f('ix_delivery_orders_status'), table_name='delivery_orders')
    op.drop_index(op.f('ix_delivery_orders_producer_id'), table_name='delivery_orders')
    op.drop_column('delivery_orders', 'total_quantity')
    op.drop_index(op.f('ix_delivery_order_status_history_order_id'), table_name='delivery_order_status_history')
    op.create_table('delivery_order_points',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('order_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('delivery_point_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('status', postgresql.ENUM('pending', 'in_transit', 'delivered', 'failed', name='deliverypointstatus'), autoincrement=False, nullable=False),
    sa.Column('quantity', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('photo_url', sa.VARCHAR(length=500), autoincrement=False, nullable=True),
    sa.Column('delivery_notes', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('delivered_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['delivery_point_id'], ['geo_delivery_points.id'], name=op.f('delivery_order_points_delivery_point_id_fkey'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['order_id'], ['delivery_orders.id'], name=op.f('delivery_order_points_order_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('delivery_order_points_pkey'))
    )
    op.create_index(op.f('ix_delivery_order_points_id'), 'delivery_order_points', ['id'], unique=False)
    op.drop_index(op.f('ix_delivery_template_points_template_id'), table_name='delivery_template_points')
    op.drop_index(op.f('ix_delivery_template_points_id'), table_name='delivery_template_points')
    op.drop_index(op.f('ix_delivery_template_points_delivery_point_id'), table_name='delivery_template_points')
    op.drop_table('delivery_template_points')
    op.drop_index(op.f('ix_delivery_order_item_points_status'), table_name='delivery_order_item_points')
    op.drop_index(op.f('ix_delivery_order_item_points_order_item_id'), table_name='delivery_order_item_points')
    op.drop_index(op.f('ix_delivery_order_item_points_id'), table_name='delivery_order_item_points')
    op.drop_index(op.f('ix_delivery_order_item_points_delivery_point_id'), table_name='delivery_order_item_points')
    op.drop_table('delivery_order_item_points')
    op.drop_index(op.f('ix_delivery_order_items_template_id'), table_name='delivery_order_items')
    op.drop_index(op.f('ix_delivery_order_items_region_id'), table_name='delivery_order_items')
    op.drop_index(op.f('ix_delivery_order_items_producer_sku_id'), table_name='delivery_order_items')
    op.drop_index(op.f('ix_delivery_order_items_order_id'), table_name='delivery_order_items')
    op.drop_index(op.f('ix_delivery_order_items_id'), table_name='delivery_order_items')
    op.drop_table('delivery_order_items')
    op.drop_index(op.f('ix_delivery_templates_region_id'), table_name='delivery_templates')
    op.drop_index(op.f('ix_delivery_templates_producer_sku_id'), table_name='delivery_templates')
    op.drop_index(op.f('ix_delivery_templates_producer_id'), table_name='delivery_templates')
    op.drop_index(op.f('ix_delivery_templates_is_active'), table_name='delivery_templates')
    op.drop_index(op.f('ix_delivery_templates_id'), table_name='delivery_templates')
    op.drop_table('delivery_templates')
