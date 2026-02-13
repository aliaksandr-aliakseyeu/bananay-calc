"""Add delivery point suggestions table (producer-submitted, pending moderation)

Revision ID: o9p0q1r2s3t4
Revises: n8o9p0q1r2s3
Create Date: 2026-02-06 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from geoalchemy2 import Geometry
from alembic import op

revision: str = "o9p0q1r2s3t4"
down_revision: Union[str, None] = "56c3ab98d1e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create geo_delivery_point_suggestions and geo_delivery_point_suggestion_tags."""
    op.create_table(
        "geo_delivery_point_suggestions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=100), nullable=True),
        sa.Column("title", sa.Text(), nullable=True, comment="Title (additional description)"),
        sa.Column("settlement_id", sa.Integer(), nullable=False),
        sa.Column("district_id", sa.Integer(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("address_comment", sa.Text(), nullable=True),
        sa.Column("landmark", sa.String(length=255), nullable=True),
        sa.Column(
            "location",
            Geometry(geometry_type="POINT", srid=4326, dimension=2, spatial_index=False),
            nullable=False,
        ),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("subcategory_id", sa.Integer(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("mobile", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("schedule", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["category_id"], ["geo_categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["geo_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["district_id"], ["geo_districts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["settlement_id"], ["geo_settlements.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subcategory_id"], ["geo_subcategories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_geo_delivery_point_suggestions_id"),
        "geo_delivery_point_suggestions",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_geo_delivery_point_suggestions_name"),
        "geo_delivery_point_suggestions",
        ["name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_geo_delivery_point_suggestions_settlement_id"),
        "geo_delivery_point_suggestions",
        ["settlement_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_geo_delivery_point_suggestions_district_id"),
        "geo_delivery_point_suggestions",
        ["district_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_geo_delivery_point_suggestions_category_id"),
        "geo_delivery_point_suggestions",
        ["category_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_geo_delivery_point_suggestions_subcategory_id"),
        "geo_delivery_point_suggestions",
        ["subcategory_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_geo_delivery_point_suggestions_created_by_id"),
        "geo_delivery_point_suggestions",
        ["created_by_id"],
        unique=False,
    )
    op.create_geospatial_index(
        "idx_geo_delivery_point_suggestions_location",
        "geo_delivery_point_suggestions",
        ["location"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={},
    )

    op.create_table(
        "geo_delivery_point_suggestion_tags",
        sa.Column("suggestion_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["suggestion_id"],
            ["geo_delivery_point_suggestions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["tag_id"], ["geo_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("suggestion_id", "tag_id"),
    )


def downgrade() -> None:
    """Drop delivery point suggestions tables."""
    op.drop_table("geo_delivery_point_suggestion_tags")
    op.drop_geospatial_index(
        "idx_geo_delivery_point_suggestions_location",
        table_name="geo_delivery_point_suggestions",
        postgresql_using="gist",
        column_name="location",
    )
    op.drop_index(
        op.f("ix_geo_delivery_point_suggestions_subcategory_id"),
        table_name="geo_delivery_point_suggestions",
    )
    op.drop_index(
        op.f("ix_geo_delivery_point_suggestions_category_id"),
        table_name="geo_delivery_point_suggestions",
    )
    op.drop_index(
        op.f("ix_geo_delivery_point_suggestions_district_id"),
        table_name="geo_delivery_point_suggestions",
    )
    op.drop_index(
        op.f("ix_geo_delivery_point_suggestions_created_by_id"),
        table_name="geo_delivery_point_suggestions",
    )
    op.drop_index(
        op.f("ix_geo_delivery_point_suggestions_settlement_id"),
        table_name="geo_delivery_point_suggestions",
    )
    op.drop_index(
        op.f("ix_geo_delivery_point_suggestions_name"),
        table_name="geo_delivery_point_suggestions",
    )
    op.drop_index(
        op.f("ix_geo_delivery_point_suggestions_id"),
        table_name="geo_delivery_point_suggestions",
    )
    op.drop_table("geo_delivery_point_suggestions")
