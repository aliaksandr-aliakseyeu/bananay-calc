"""Add JSONB i18n name fields to countries and regions.

Revision ID: h0i1j2k3l4m5
Revises: g9h0i1j2k3l4
Create Date: 2026-06-25 14:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "h0i1j2k3l4m5"
down_revision: Union[str, None] = "g9h0i1j2k3l4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "geo_countries",
        sa.Column(
            "name_i18n",
            JSONB,
            nullable=True,
            comment="Localized country names (en, ka, ru)",
        ),
    )
    op.add_column(
        "geo_regions",
        sa.Column(
            "name_i18n",
            JSONB,
            nullable=True,
            comment="Localized region names (en, ka, ru)",
        ),
    )

    op.execute(
        """
        UPDATE geo_countries
        SET name_i18n = jsonb_build_object('ru', name)
        """
    )
    op.execute(
        """
        UPDATE geo_regions
        SET name_i18n = jsonb_build_object('ru', name)
        """
    )

    op.execute(
        """
        UPDATE geo_countries
        SET name_i18n = name_i18n || jsonb_build_object(
            'en', CASE code
                WHEN 'GE' THEN 'Georgia'
                WHEN 'RU' THEN 'Russia'
                WHEN 'BY' THEN 'Belarus'
                ELSE COALESCE(name_i18n->>'en', name)
            END,
            'ka', CASE code
                WHEN 'GE' THEN 'საქართეთი'
                WHEN 'RU' THEN 'რუსეთი'
                WHEN 'BY' THEN 'ბელარუსი'
                ELSE COALESCE(name_i18n->>'ka', name)
            END
        )
        """
    )

    op.execute(
        """
        UPDATE geo_regions
        SET name_i18n = name_i18n || jsonb_build_object(
            'en', CASE name
                WHEN 'Батуми' THEN 'Batumi'
                WHEN 'Краснодарский край' THEN 'Krasnodar Krai'
                WHEN 'Московская область' THEN 'Moscow Oblast'
                ELSE COALESCE(name_i18n->>'en', name)
            END,
            'ka', CASE name
                WHEN 'Батуми' THEN 'ბათუმი'
                WHEN 'Краснодарский край' THEN 'კრასნოდარის რკალი'
                WHEN 'Московская область' THEN 'მოსკოვის ობლასტი'
                ELSE COALESCE(name_i18n->>'ka', name)
            END
        )
        """
    )

    op.execute(
        """
        UPDATE geo_countries
        SET name = COALESCE(name_i18n->>'en', name)
        """
    )
    op.execute(
        """
        UPDATE geo_regions
        SET name = COALESCE(name_i18n->>'en', name)
        """
    )

    op.alter_column("geo_countries", "name_i18n", nullable=False)
    op.alter_column("geo_regions", "name_i18n", nullable=False)

    op.drop_index("ix_geo_countries_name", table_name="geo_countries")
    op.create_index(
        "ix_geo_countries_name",
        "geo_countries",
        ["name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_geo_countries_name", table_name="geo_countries")
    op.create_index(
        "ix_geo_countries_name",
        "geo_countries",
        ["name"],
        unique=True,
    )

    op.drop_column("geo_regions", "name_i18n")
    op.drop_column("geo_countries", "name_i18n")
