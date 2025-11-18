"""add_delivery_points_search_support

Revision ID: 109cbe768b76
Revises: bc6c4f2244d4
Create Date: 2025-11-17 13:56:42.115065

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '109cbe768b76'
down_revision: Union[str, Sequence[str], None] = 'bc6c4f2244d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add search support for delivery points.

    - Enable pg_trgm extension for fuzzy search and autocomplete
    - Add name_normalized generated column for optimized search
    - Create GIN index for fast search queries
    """
    # 1. Enable pg_trgm extension for fuzzy search and autocomplete
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm;')

    # 2. Add normalized name column (auto-computed from name)
    # Normalization rules:
    # - Convert to lowercase
    # - Replace ё with е (Russian language normalization)
    # - Remove all special characters (keep only letters, numbers, spaces)
    # - Collapse multiple spaces into one
    op.execute("""
        ALTER TABLE delivery_points
        ADD COLUMN name_normalized TEXT
        GENERATED ALWAYS AS (
          trim(regexp_replace(
            regexp_replace(
              regexp_replace(lower(name), 'ё', 'е', 'g'),
              '[^а-яa-z0-9\\s]', ' ', 'g'
            ),
            '\\s+', ' ', 'g'
          ))
        ) STORED;
    """)

    # 3. Create GIN index for fast trigram-based search
    # This enables fast LIKE/ILIKE queries and similarity search
    op.execute("""
        CREATE INDEX idx_delivery_points_name_normalized_trgm
        ON delivery_points USING GIN (name_normalized gin_trgm_ops);
    """)


def downgrade() -> None:
    """Remove search support for delivery points."""
    # Remove index
    op.execute('DROP INDEX IF EXISTS idx_delivery_points_name_normalized_trgm;')

    # Remove normalized column
    op.execute('ALTER TABLE delivery_points DROP COLUMN IF EXISTS name_normalized;')

    # Note: We don't drop pg_trgm extension as it might be used by other features
