"""merge heads

Revision ID: h2i3j4k5l6m7
Revises: b2c3d4e5f6a7, a1b2c3d4e5f7
Create Date: 2026-01-20 16:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'h2i3j4k5l6m7'
down_revision: Union[str, Sequence[str], None] = ('b2c3d4e5f6a7', 'a1b2c3d4e5f7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge two heads: b2c3d4e5f6a7 and a1b2c3d4e5f7."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass



