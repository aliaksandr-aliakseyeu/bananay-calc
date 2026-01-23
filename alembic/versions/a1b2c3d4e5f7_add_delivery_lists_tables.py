"""add delivery lists tables

Revision ID: a1b2c3d4e5f7
Revises: f1a2b3c4d5e6, bc6c4f2244d4
Create Date: 2026-01-20 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, Sequence[str], None] = ('f1a2b3c4d5e6', 'bc6c4f2244d4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        'geo_delivery_lists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['geo_users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'name', name='uq_user_list_name')
    )
    op.create_index('ix_geo_delivery_lists_id', 'geo_delivery_lists', ['id'])
    op.create_index('ix_geo_delivery_lists_user_id', 'geo_delivery_lists', ['user_id'])
    op.create_index('ix_geo_delivery_lists_is_default', 'geo_delivery_lists', ['is_default'])

    op.create_table(
        'geo_delivery_list_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('list_id', sa.Integer(), nullable=False),
        sa.Column('delivery_point_id', sa.Integer(), nullable=False),
        sa.Column('custom_name', sa.String(length=200), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['list_id'], ['geo_delivery_lists.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['delivery_point_id'], ['geo_delivery_points.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('list_id', 'delivery_point_id', name='uq_list_delivery_point')
    )
    op.create_index('ix_geo_delivery_list_items_id', 'geo_delivery_list_items', ['id'])
    op.create_index('ix_geo_delivery_list_items_list_id', 'geo_delivery_list_items', ['list_id'])
    op.create_index('ix_geo_delivery_list_items_delivery_point_id', 'geo_delivery_list_items', ['delivery_point_id'])


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index('ix_geo_delivery_list_items_delivery_point_id', 'geo_delivery_list_items')
    op.drop_index('ix_geo_delivery_list_items_list_id', 'geo_delivery_list_items')
    op.drop_index('ix_geo_delivery_list_items_id', 'geo_delivery_list_items')
    op.drop_table('geo_delivery_list_items')

    op.drop_index('ix_geo_delivery_lists_is_default', 'geo_delivery_lists')
    op.drop_index('ix_geo_delivery_lists_user_id', 'geo_delivery_lists')
    op.drop_index('ix_geo_delivery_lists_id', 'geo_delivery_lists')
    op.drop_table('geo_delivery_lists')
    op.drop_table('geo_delivery_lists')
