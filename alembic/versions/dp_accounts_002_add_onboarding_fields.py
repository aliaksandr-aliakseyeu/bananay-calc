"""Add delivery point onboarding fields and statuses.

Revision ID: dp_accounts_002
Revises: dp_accounts_001
Create Date: 2026-03-17
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "dp_accounts_002"
down_revision: Union[str, None] = "dp_accounts_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("delivery_point_accounts", sa.Column("about_text", sa.Text(), nullable=True))
    op.add_column(
        "delivery_point_accounts",
        sa.Column("requested_delivery_point_ids", sa.JSON(), nullable=True),
    )
    op.add_column(
        "delivery_point_accounts",
        sa.Column("application_submitted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "delivery_point_accounts",
        sa.Column("application_reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "delivery_point_accounts",
        sa.Column("application_reviewed_by", sa.Integer(), nullable=True),
    )
    op.add_column(
        "delivery_point_accounts",
        sa.Column("application_reject_reason", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_delivery_point_accounts_application_reviewed_by_geo_users",
        "delivery_point_accounts",
        "geo_users",
        ["application_reviewed_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_delivery_point_accounts_application_reviewed_by",
        "delivery_point_accounts",
        ["application_reviewed_by"],
        unique=False,
    )

    op.execute(
        sa.text(
            """
            ALTER TABLE delivery_point_accounts
            ALTER COLUMN status TYPE VARCHAR(50)
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE delivery_point_accounts
            ALTER COLUMN status TYPE VARCHAR(20)
            """
        )
    )

    op.drop_index(
        "ix_delivery_point_accounts_application_reviewed_by",
        table_name="delivery_point_accounts",
    )
    op.drop_constraint(
        "fk_delivery_point_accounts_application_reviewed_by_geo_users",
        "delivery_point_accounts",
        type_="foreignkey",
    )
    op.drop_column("delivery_point_accounts", "application_reject_reason")
    op.drop_column("delivery_point_accounts", "application_reviewed_by")
    op.drop_column("delivery_point_accounts", "application_reviewed_at")
    op.drop_column("delivery_point_accounts", "application_submitted_at")
    op.drop_column("delivery_point_accounts", "requested_delivery_point_ids")
    op.drop_column("delivery_point_accounts", "about_text")
