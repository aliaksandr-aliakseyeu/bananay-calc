"""Add verification_reject_reason to vehicle_compliance.

Revision ID: e7f8g9h0i1j2
Revises: c6d7e8f9g0h1
Create Date: 2026-04-15 18:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7f8g9h0i1j2"
down_revision: Union[str, None] = "c6d7e8f9g0h1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "vehicle_compliance",
        sa.Column("verification_reject_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vehicle_compliance", "verification_reject_reason")
