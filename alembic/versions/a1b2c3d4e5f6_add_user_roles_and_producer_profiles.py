"""add user roles and producer profiles

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-01-14 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        'geo_users',
        sa.Column('role', sa.String(length=50), nullable=False, server_default='producer')
    )
    op.add_column(
        'geo_users',
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column('geo_users', sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('geo_users', sa.Column('is_approved', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('geo_users', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('geo_users', sa.Column('approved_by', sa.Integer(), nullable=True))
    op.add_column('geo_users', sa.Column('is_rejected', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('geo_users', sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('geo_users', sa.Column('rejected_by', sa.Integer(), nullable=True))
    op.add_column(
        'geo_users',
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('now()')
        )
    )

    op.create_index('ix_geo_users_role', 'geo_users', ['role'])
    op.create_index('ix_geo_users_is_approved', 'geo_users', ['is_approved'])

    op.create_foreign_key(
        'fk_geo_users_approved_by',
        'geo_users', 'geo_users',
        ['approved_by'], ['id']
    )
    op.create_foreign_key(
        'fk_geo_users_rejected_by',
        'geo_users', 'geo_users',
        ['rejected_by'], ['id']
    )

    op.create_table(
        'producer_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('company_name', sa.String(length=500), nullable=False),
        sa.Column('company_inn', sa.String(length=12), nullable=True),
        sa.Column('contact_person', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('company_address', sa.String(length=1000), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('website', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['geo_users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id'),
        sa.UniqueConstraint('company_inn')
    )

    op.create_index('ix_producer_profiles_id', 'producer_profiles', ['id'])
    op.create_index('ix_producer_profiles_user_id', 'producer_profiles', ['user_id'])
    op.create_index('ix_producer_profiles_company_inn', 'producer_profiles', ['company_inn'])

    op.execute("""
        UPDATE geo_users
        SET role = 'ADMIN',
            email_verified = true,
            email_verified_at = now(),
            is_approved = true,
            approved_at = now()
        WHERE email = 'gollum80@gmail.com';
    """)


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index('ix_producer_profiles_company_inn', table_name='producer_profiles')
    op.drop_index('ix_producer_profiles_user_id', table_name='producer_profiles')
    op.drop_index('ix_producer_profiles_id', table_name='producer_profiles')
    op.drop_table('producer_profiles')

    op.drop_constraint('fk_geo_users_rejected_by', 'geo_users', type_='foreignkey')
    op.drop_constraint('fk_geo_users_approved_by', 'geo_users', type_='foreignkey')

    op.drop_index('ix_geo_users_is_approved', table_name='geo_users')
    op.drop_index('ix_geo_users_role', table_name='geo_users')

    op.drop_column('geo_users', 'updated_at')
    op.drop_column('geo_users', 'rejected_by')
    op.drop_column('geo_users', 'rejected_at')
    op.drop_column('geo_users', 'is_rejected')
    op.drop_column('geo_users', 'approved_by')
    op.drop_column('geo_users', 'approved_at')
    op.drop_column('geo_users', 'is_approved')
    op.drop_column('geo_users', 'email_verified_at')
    op.drop_column('geo_users', 'email_verified')
    op.drop_column('geo_users', 'role')
