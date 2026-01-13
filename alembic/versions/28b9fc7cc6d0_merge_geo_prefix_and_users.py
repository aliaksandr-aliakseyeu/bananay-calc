"""merge_geo_prefix_and_users

Revision ID: 28b9fc7cc6d0
Revises: 13d596b1b334, dca6b2a2dc5f
Create Date: 2025-12-23 10:29:12.982950

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28b9fc7cc6d0'
down_revision: Union[str, Sequence[str], None] = ('13d596b1b334', 'dca6b2a2dc5f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
