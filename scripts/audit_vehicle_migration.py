"""
Audit data quality before removing legacy vehicle columns.

Usage:
    poetry run python scripts/audit_vehicle_migration.py
"""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import AsyncSessionLocal  # noqa: E402


QUERIES = {
    "duplicate_plate_number_normalized": """
        SELECT plate_number_normalized, COUNT(*) AS duplicate_count
        FROM driver_vehicles
        WHERE plate_number_normalized IS NOT NULL
        GROUP BY plate_number_normalized
        HAVING COUNT(*) > 1
        ORDER BY duplicate_count DESC, plate_number_normalized
    """,
    "vehicles_missing_capabilities": """
        SELECT dv.id, dv.driver_id, dv.plate_number
        FROM driver_vehicles dv
        LEFT JOIN vehicle_capabilities vc ON vc.vehicle_id = dv.id
        WHERE vc.vehicle_id IS NULL
        ORDER BY dv.created_at
    """,
    "vehicles_missing_compliance": """
        SELECT dv.id, dv.driver_id, dv.plate_number
        FROM driver_vehicles dv
        LEFT JOIN vehicle_compliance vc ON vc.vehicle_id = dv.id
        WHERE vc.vehicle_id IS NULL
        ORDER BY dv.created_at
    """,
    "active_vehicles_without_sts": """
        SELECT id, driver_id, plate_number
        FROM driver_vehicles
        WHERE status IN (1, 2, 3)
          AND sts_media_id IS NULL
        ORDER BY created_at
    """,
    "orphan_vehicle_media": """
        SELECT mf.id, mf.owner_id, mf.kind, mf.created_at
        FROM media_files mf
        LEFT JOIN driver_vehicles dv
          ON dv.id = mf.owner_id
        WHERE mf.owner_type = 'vehicle'
          AND dv.id IS NULL
        ORDER BY mf.created_at DESC
    """,
    "unknown_body_type_codes": """
        SELECT id, plate_number, body_type_code
        FROM driver_vehicles
        WHERE COALESCE(body_type_code, 0) IN (0, 99)
        ORDER BY created_at
    """,
    "vehicles_missing_payload": """
        SELECT dv.id, dv.plate_number
        FROM driver_vehicles dv
        JOIN vehicle_capabilities vc ON vc.vehicle_id = dv.id
        WHERE vc.payload_kg IS NULL OR vc.payload_kg <= 0
        ORDER BY dv.created_at
    """,
}


async def main() -> None:
    async with AsyncSessionLocal() as session:
        for title, query in QUERIES.items():
            result = await session.execute(text(query))
            rows = result.fetchall()
            print(f"\n[{title}] count={len(rows)}")
            for row in rows[:20]:
                print(dict(row._mapping))
            if len(rows) > 20:
                print(f"... truncated, remaining rows: {len(rows) - 20}")


if __name__ == "__main__":
    asyncio.run(main())
