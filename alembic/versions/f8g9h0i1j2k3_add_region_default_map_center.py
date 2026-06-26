"""Add default map center fields to geo_regions.

Revision ID: f8g9h0i1j2k3
Revises: e7f8g9h0i1j2
Create Date: 2026-06-24 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f8g9h0i1j2k3"
down_revision: Union[str, None] = "e7f8g9h0i1j2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "geo_regions",
        sa.Column("default_lat", sa.Float(), nullable=True, comment="Default map center latitude"),
    )
    op.add_column(
        "geo_regions",
        sa.Column("default_lng", sa.Float(), nullable=True, comment="Default map center longitude"),
    )


def downgrade() -> None:
    op.drop_column("geo_regions", "default_lng")
    op.drop_column("geo_regions", "default_lat")
