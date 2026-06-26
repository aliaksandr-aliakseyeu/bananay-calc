"""Add JSONB schedule_i18n to delivery points.

Revision ID: i1j2k3l4m5n6
Revises: h0i1j2k3l4m5
Create Date: 2026-06-25 16:00:00.000000

Data backfill: run scripts/backfill_schedule_i18n.py (shows progress bar).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "i1j2k3l4m5n6"
down_revision: Union[str, None] = "h0i1j2k3l4m5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "geo_delivery_points",
        sa.Column(
            "schedule_i18n",
            JSONB,
            nullable=True,
            comment="Localized working hours (en, ka, ru)",
        ),
    )
    print(
        "Column schedule_i18n added. "
        "Run: python scripts/backfill_schedule_i18n.py"
    )


def downgrade() -> None:
    op.drop_column("geo_delivery_points", "schedule_i18n")
