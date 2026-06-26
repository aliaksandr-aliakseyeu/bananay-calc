"""Helpers for keeping PostgreSQL serial sequences in sync."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def sync_table_id_sequence(db: AsyncSession, table_name: str) -> None:
    """Set table id sequence to MAX(id) so the next INSERT gets a free id."""
    await db.execute(
        text(
            f"SELECT setval("
            f"pg_get_serial_sequence('{table_name}', 'id'), "
            f"GREATEST(COALESCE((SELECT MAX(id) FROM {table_name}), 0), 1), "
            f"true)"
        )
    )
