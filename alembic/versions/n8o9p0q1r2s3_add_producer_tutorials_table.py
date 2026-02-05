"""Add producer tutorials table

Revision ID: n8o9p0q1r2s3
Revises: m7n8o9p0q1r2
Create Date: 2026-01-26 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = 'n8o9p0q1r2s3'
down_revision: Union[str, None] = 'm7n8o9p0q1r2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add producer tutorials table and show_tooltips field to users."""

    op.execute("""
        CREATE TYPE tutorialtype AS ENUM (
            'DASHBOARD_WELCOME',
            'DELIVERY_LISTS',
            'PRODUCT_SKU',
            'DELIVERY_ORDERS'
        )
    """)

    op.execute("""
        CREATE TYPE tutorialstatus AS ENUM (
            'NOT_STARTED',
            'IN_PROGRESS',
            'COMPLETED',
            'SKIPPED'
        )
    """)

    op.create_table(
        'producer_tutorials',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('producer_id', sa.Integer(), nullable=False),
        sa.Column('tutorial_type', sa.Enum(
            'DASHBOARD_WELCOME',
            'DELIVERY_LISTS',
            'PRODUCT_SKU',
            'DELIVERY_ORDERS',
            name='tutorialtype',
            native_enum=False,
            length=50
        ), nullable=False),
        sa.Column('status', sa.Enum(
            'NOT_STARTED',
            'IN_PROGRESS',
            'COMPLETED',
            'SKIPPED',
            name='tutorialstatus',
            native_enum=False,
            length=50
        ), nullable=False, server_default='NOT_STARTED'),
        sa.Column('current_step', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_shown_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['producer_id'], ['geo_users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_producer_tutorials_id'), 'producer_tutorials', ['id'], unique=False)
    op.create_index(op.f('ix_producer_tutorials_producer_id'), 'producer_tutorials', ['producer_id'], unique=False)
    op.create_index(op.f('ix_producer_tutorials_tutorial_type'), 'producer_tutorials', ['tutorial_type'], unique=False)

    op.create_unique_constraint('uq_producer_tutorial_type', 'producer_tutorials', ['producer_id', 'tutorial_type'])

    op.add_column('geo_users', sa.Column('show_tooltips', sa.Boolean(), nullable=False, server_default='true'))


def downgrade() -> None:
    """Remove producer tutorials table and show_tooltips field."""

    op.drop_column('geo_users', 'show_tooltips')

    op.drop_constraint('uq_producer_tutorial_type', 'producer_tutorials', type_='unique')
    op.drop_index(op.f('ix_producer_tutorials_tutorial_type'), table_name='producer_tutorials')
    op.drop_index(op.f('ix_producer_tutorials_producer_id'), table_name='producer_tutorials')
    op.drop_index(op.f('ix_producer_tutorials_id'), table_name='producer_tutorials')

    op.drop_table('producer_tutorials')

    op.execute('DROP TYPE tutorialstatus')
    op.execute('DROP TYPE tutorialtype')
