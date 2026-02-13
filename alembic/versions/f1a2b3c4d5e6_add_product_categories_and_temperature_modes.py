"""add product categories and temperature modes

Revision ID: f1a2b3c4d5e6
Revises: bc6c4f2244d4
Create Date: 2026-01-12 15:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = '28b9fc7cc6d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    op.add_column('geo_product_categories', 
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='Активность категории'))
    op.add_column('geo_product_categories',
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0', comment='Порядок сортировки'))
    
    op.create_unique_constraint('uq_geo_product_categories_name', 'geo_product_categories', ['name'])
    op.create_unique_constraint('uq_geo_product_categories_slug', 'geo_product_categories', ['slug'])
    
    op.create_table(
        'geo_temperature_modes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False, comment='Название температурного режима'),
        sa.Column('slug', sa.String(length=100), nullable=False, comment='URL-friendly название'),
        sa.Column('description', sa.Text(), nullable=True, comment='Описание режима'),
        sa.Column('cost_multiplier', sa.Numeric(precision=5, scale=2), nullable=False, server_default='1.0', comment='Множитель стоимости'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='Активность режима'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0', comment='Порядок сортировки'),
        sa.Column('min_temperature', sa.Integer(), nullable=True, comment='Минимальная температура'),
        sa.Column('max_temperature', sa.Integer(), nullable=True, comment='Максимальная температура'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    
    op.create_index('ix_geo_temperature_modes_id', 'geo_temperature_modes', ['id'])
    op.create_index('ix_geo_temperature_modes_name', 'geo_temperature_modes', ['name'])
    op.create_index('ix_geo_temperature_modes_slug', 'geo_temperature_modes', ['slug'])
    
    op.execute("""
        INSERT INTO geo_product_categories (name, slug, description, cost_multiplier, is_active, sort_order)
        VALUES
            ('Свежие продукты', 'svezhie-produkty', 'Свежие фрукты, овощи, зелень и другие продукты', 1.0, true, 10),
            ('Замороженные', 'zamorozhennye', 'Замороженные продукты и полуфабрикаты', 1.2, true, 20),
            ('Сухие товары', 'suhie-tovary', 'Сухие продукты, крупы, консервы', 1.0, true, 30),
            ('Другое', 'drugoe', 'Прочие категории товаров', 1.0, true, 40);
    """)
    
    op.execute("""
        INSERT INTO geo_temperature_modes (name, slug, description, cost_multiplier, is_active, sort_order, min_temperature, max_temperature)
        VALUES
            ('Комнатная температура (+15°C до +25°C)', 'room-temperature', 'Товары, не требующие особых условий хранения', 1.0, true, 10, 15, 25),
            ('Охлажденный (0°C до +8°C)', 'chilled', 'Охлажденные продукты', 1.3, true, 20, 0, 8),
            ('Замороженный (-18°C и ниже)', 'frozen', 'Замороженные продукты', 1.5, true, 30, -25, -18);
    """)


def downgrade() -> None:
    """Downgrade schema."""
    
    op.drop_index('ix_geo_temperature_modes_slug', table_name='geo_temperature_modes')
    op.drop_index('ix_geo_temperature_modes_name', table_name='geo_temperature_modes')
    op.drop_index('ix_geo_temperature_modes_id', table_name='geo_temperature_modes')
    
    op.drop_table('geo_temperature_modes')
    
    op.drop_constraint('uq_geo_product_categories_slug', 'geo_product_categories', type_='unique')
    op.drop_constraint('uq_geo_product_categories_name', 'geo_product_categories', type_='unique')
    op.drop_column('geo_product_categories', 'sort_order')
    op.drop_column('geo_product_categories', 'is_active')

