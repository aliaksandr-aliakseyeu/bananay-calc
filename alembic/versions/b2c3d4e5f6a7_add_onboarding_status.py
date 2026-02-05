"""add onboarding status

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-15 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        'geo_users',
        sa.Column(
            'onboarding_status',
            sa.String(length=50),
            nullable=False,
            server_default='pending_email_verification'
        )
    )

    op.create_index(
        'ix_geo_users_onboarding_status',
        'geo_users',
        ['onboarding_status']
    )

    op.execute("""
        UPDATE geo_users
        SET onboarding_status = 'COMPLETED'
        WHERE role = 'ADMIN';
    """)


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index('ix_geo_users_onboarding_status', table_name='geo_users')

    op.drop_column('geo_users', 'onboarding_status')
