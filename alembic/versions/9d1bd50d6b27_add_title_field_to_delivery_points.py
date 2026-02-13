"""add title field to delivery points

Revision ID: 9d1bd50d6b27
Revises: 096e992f191b
Create Date: 2025-11-13 10:03:45.762888

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9d1bd50d6b27'
down_revision: Union[str, Sequence[str], None] = '096e992f191b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('delivery_points', sa.Column('title', sa.Text(), nullable=True, comment='Заголовок (дополнительное описание)'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('delivery_points', 'title')
