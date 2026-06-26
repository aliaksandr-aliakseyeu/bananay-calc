import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.db.base import engine


async def main() -> None:
    async with engine.begin() as conn:
        max_result = await conn.execute(text("SELECT MAX(id) FROM geo_sectors"))
        print("max_id:", max_result.scalar())
        await conn.execute(
            text(
                "SELECT setval("
                "pg_get_serial_sequence('geo_sectors', 'id'), "
                "GREATEST(COALESCE((SELECT MAX(id) FROM geo_sectors), 0), 1), "
                "true)"
            )
        )
    await engine.dispose()
    print("geo_sectors sequence synced (next id will be MAX(id)+1)")


if __name__ == "__main__":
    asyncio.run(main())
