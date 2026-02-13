"""update sku dimensions to decimal

Revision ID: i3j4k5l6m7n8
Revises: g1h2i3j4k5l6
Create Date: 2026-01-22 20:00:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = 'i3j4k5l6m7n8'
down_revision = 'g1h2i3j4k5l6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('producer_skus', 'length_cm',
                    existing_type=sa.Integer(),
                    type_=sa.Numeric(10, 2),
                    existing_nullable=False,
                    postgresql_using='length_cm::numeric(10,2)')
    
    op.alter_column('producer_skus', 'width_cm',
                    existing_type=sa.Integer(),
                    type_=sa.Numeric(10, 2),
                    existing_nullable=False,
                    postgresql_using='width_cm::numeric(10,2)')
    
    op.alter_column('producer_skus', 'height_cm',
                    existing_type=sa.Integer(),
                    type_=sa.Numeric(10, 2),
                    existing_nullable=False,
                    postgresql_using='height_cm::numeric(10,2)')
    
    op.alter_column('producer_skus', 'items_per_box',
                    existing_type=sa.Integer(),
                    nullable=True,
                    existing_nullable=False)


def downgrade() -> None:
    op.execute("UPDATE producer_skus SET items_per_box = 1 WHERE items_per_box IS NULL")
    op.alter_column('producer_skus', 'items_per_box',
                    existing_type=sa.Integer(),
                    nullable=False,
                    existing_nullable=True)
    
    op.alter_column('producer_skus', 'height_cm',
                    existing_type=sa.Numeric(10, 2),
                    type_=sa.Integer(),
                    existing_nullable=False,
                    postgresql_using='height_cm::integer')
    
    op.alter_column('producer_skus', 'width_cm',
                    existing_type=sa.Numeric(10, 2),
                    type_=sa.Integer(),
                    existing_nullable=False,
                    postgresql_using='width_cm::integer')
    
    op.alter_column('producer_skus', 'length_cm',
                    existing_type=sa.Numeric(10, 2),
                    type_=sa.Integer(),
                    existing_nullable=False,
                    postgresql_using='length_cm::integer')


