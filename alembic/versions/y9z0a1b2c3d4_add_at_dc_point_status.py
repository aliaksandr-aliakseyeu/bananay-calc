"""Add at_dc to delivery point status and loading_at_warehouse to order status

Revision ID: y9z0a1b2c3d4
Revises: x8y9z0a1b2c3
Create Date: 2026-02-16

"""
from typing import Sequence, Union

from alembic import op

revision: str = "y9z0a1b2c3d4"
down_revision: Union[str, None] = "x8y9z0a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            ALTER TYPE deliverypointstatus ADD VALUE 'at_dc';
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            ALTER TYPE orderstatus ADD VALUE 'loading_at_warehouse';
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """)


def downgrade() -> None:
    pass
