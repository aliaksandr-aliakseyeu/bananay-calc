"""Add JSONB i18n fields to product categories and temperature modes.

Revision ID: g9h0i1j2k3l4
Revises: f8g9h0i1j2k3
Create Date: 2026-06-25 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "g9h0i1j2k3l4"
down_revision: Union[str, None] = "f8g9h0i1j2k3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "geo_product_categories",
        sa.Column(
            "name_i18n",
            JSONB,
            nullable=True,
            comment="Localized category names (en, ka, ru)",
        ),
    )
    op.add_column(
        "geo_product_categories",
        sa.Column(
            "description_i18n",
            JSONB,
            nullable=True,
            comment="Localized category descriptions (en, ka, ru)",
        ),
    )
    op.add_column(
        "geo_temperature_modes",
        sa.Column(
            "name_i18n",
            JSONB,
            nullable=True,
            comment="Localized mode names (en, ka, ru)",
        ),
    )
    op.add_column(
        "geo_temperature_modes",
        sa.Column(
            "description_i18n",
            JSONB,
            nullable=True,
            comment="Localized mode descriptions (en, ka, ru)",
        ),
    )

    # Seed i18n from legacy Russian columns.
    op.execute(
        """
        UPDATE geo_product_categories
        SET
            name_i18n = jsonb_build_object('ru', name),
            description_i18n = CASE
                WHEN description IS NOT NULL THEN jsonb_build_object('ru', description)
                ELSE NULL
            END
        """
    )
    op.execute(
        """
        UPDATE geo_temperature_modes
        SET
            name_i18n = jsonb_build_object('ru', name),
            description_i18n = CASE
                WHEN description IS NOT NULL THEN jsonb_build_object('ru', description)
                ELSE NULL
            END
        """
    )

    # English and Georgian translations for known slugs.
    op.execute(
        """
        UPDATE geo_product_categories
        SET
            name_i18n = name_i18n || jsonb_build_object(
                'en', CASE slug
                    WHEN 'svezhie-produkty' THEN 'Fresh products'
                    WHEN 'zamorozhennye' THEN 'Frozen'
                    WHEN 'suhie-tovary' THEN 'Dry goods'
                    WHEN 'drugoe' THEN 'Other'
                    ELSE COALESCE(name_i18n->>'en', name)
                END,
                'ka', CASE slug
                    WHEN 'svezhie-produkty' THEN 'ახალი პროდუქტები'
                    WHEN 'zamorozhennye' THEN 'გაყინული'
                    WHEN 'suhie-tovary' THEN 'მშრალი საქონელი'
                    WHEN 'drugoe' THEN 'სხვა'
                    ELSE COALESCE(name_i18n->>'ka', name)
                END
            ),
            description_i18n = CASE
                WHEN description IS NOT NULL THEN COALESCE(description_i18n, '{}'::jsonb) || jsonb_build_object(
                    'en', CASE slug
                        WHEN 'svezhie-produkty' THEN 'Fresh fruits, vegetables, greens and other products'
                        WHEN 'zamorozhennye' THEN 'Frozen products and semi-finished goods'
                        WHEN 'suhie-tovary' THEN 'Dry goods, grains, canned food'
                        WHEN 'drugoe' THEN 'Other product categories'
                        ELSE COALESCE(description_i18n->>'en', description)
                    END,
                    'ka', CASE slug
                        WHEN 'svezhie-produkty' THEN 'ახალი ხილი, ბოსტნეული, მწვანილი და სხვა პროდუქტები'
                        WHEN 'zamorozhennye' THEN 'გაყინული პროდუქტები და ნახევარფაბრიკატები'
                        WHEN 'suhie-tovary' THEN 'მშრალი პროდუქტები, მარცვლეული, კონსერვები'
                        WHEN 'drugoe' THEN 'სხვა პროდუქტის კატეგორიები'
                        ELSE COALESCE(description_i18n->>'ka', description)
                    END
                )
                ELSE description_i18n
            END
        """
    )

    op.execute(
        """
        UPDATE geo_temperature_modes
        SET
            name_i18n = name_i18n || jsonb_build_object(
                'en', CASE slug
                    WHEN 'room-temperature' THEN 'Room temperature (+15°C to +25°C)'
                    WHEN 'chilled' THEN 'Chilled (0°C to +8°C)'
                    WHEN 'frozen' THEN 'Frozen (-18°C and below)'
                    ELSE COALESCE(name_i18n->>'en', name)
                END,
                'ka', CASE slug
                    WHEN 'room-temperature' THEN 'ოთახის ტემპერატურა (+15°C - +25°C)'
                    WHEN 'chilled' THEN 'გაციებული (0°C - +8°C)'
                    WHEN 'frozen' THEN 'გაყინული (-18°C და ქვემოთ)'
                    ELSE COALESCE(name_i18n->>'ka', name)
                END
            ),
            description_i18n = CASE
                WHEN description IS NOT NULL THEN COALESCE(description_i18n, '{}'::jsonb) || jsonb_build_object(
                    'en', CASE slug
                        WHEN 'room-temperature' THEN 'Products that do not require special storage conditions'
                        WHEN 'chilled' THEN 'Chilled products'
                        WHEN 'frozen' THEN 'Frozen products'
                        ELSE COALESCE(description_i18n->>'en', description)
                    END,
                    'ka', CASE slug
                        WHEN 'room-temperature' THEN 'პროდუქტები, რომლებსაც არ სჭირდებათ განსაკუთრებული შენახვის პირობები'
                        WHEN 'chilled' THEN 'გაციებული პროდუქტები'
                        WHEN 'frozen' THEN 'გაყინული პროდუქტები'
                        ELSE COALESCE(description_i18n->>'ka', description)
                    END
                )
                ELSE description_i18n
            END
        """
    )

    # Sync legacy columns to English for sorting and backward compatibility.
    op.execute(
        """
        UPDATE geo_product_categories
        SET
            name = COALESCE(name_i18n->>'en', name),
            description = COALESCE(description_i18n->>'en', description)
        """
    )
    op.execute(
        """
        UPDATE geo_temperature_modes
        SET
            name = COALESCE(name_i18n->>'en', name),
            description = COALESCE(description_i18n->>'en', description)
        """
    )

    op.alter_column("geo_product_categories", "name_i18n", nullable=False)
    op.alter_column("geo_temperature_modes", "name_i18n", nullable=False)

    op.drop_index("ix_geo_product_categories_name", table_name="geo_product_categories")
    op.create_index(
        "ix_geo_product_categories_name",
        "geo_product_categories",
        ["name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_geo_product_categories_name", table_name="geo_product_categories")
    op.create_index(
        "ix_geo_product_categories_name",
        "geo_product_categories",
        ["name"],
        unique=True,
    )

    op.drop_column("geo_temperature_modes", "description_i18n")
    op.drop_column("geo_temperature_modes", "name_i18n")
    op.drop_column("geo_product_categories", "description_i18n")
    op.drop_column("geo_product_categories", "name_i18n")
