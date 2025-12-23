"""add_geo_users_table

Revision ID: 13d596b1b334
Revises: eaed51cb9bb2
Create Date: 2025-12-22 12:19:01.317789

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '13d596b1b334'
down_revision: Union[str, Sequence[str], None] = 'eaed51cb9bb2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create geo_users table for authentication
    op.create_table(
        'geo_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_geo_users_email'), 'geo_users', ['email'], unique=True)
    op.create_index(op.f('ix_geo_users_id'), 'geo_users', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_geo_users_email'), table_name='geo_users')
    op.drop_index(op.f('ix_geo_users_id'), table_name='geo_users')
    op.drop_table('geo_users')
    op.drop_table('geo_users')
