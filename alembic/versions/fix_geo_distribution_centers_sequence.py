"""fix geo_distribution_centers id sequence

Revision ID: fix_dc_seq_01
Revises: 019eec32bc63
Create Date: 2026-02-16

Syncs the id sequence for geo_distribution_centers so that the next
value is greater than MAX(id). Fixes IntegrityError "duplicate key (id)=7"
when creating new distribution centers after manual data load or restore.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "fix_dc_seq_01"
down_revision: Union[str, Sequence[str], None] = "019eec32bc63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$
        DECLARE
            seq_name text := pg_get_serial_sequence('geo_distribution_centers', 'id');
            next_val bigint;
        BEGIN
            IF seq_name IS NOT NULL THEN
                SELECT COALESCE(MAX(id), 1) INTO next_val FROM geo_distribution_centers;
                EXECUTE format('SELECT setval(%L, %s)', seq_name, next_val);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    pass
