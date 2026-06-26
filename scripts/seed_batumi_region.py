"""
Idempotent seed for Georgia / Batumi region.

Usage:
    poetry run python scripts/seed_batumi_region.py
"""
import asyncio
import sys
from pathlib import Path

from sqlalchemy import select, text

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import AsyncSessionLocal
from app.db.models import Country, Region

BATUMI_LAT = 41.6168
BATUMI_LNG = 41.6367


async def _sync_id_sequence(db, table_name: str) -> None:
    await db.execute(
        text(
            f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {table_name}), 0))"
        )
    )


async def seed_batumi_region() -> None:
    async with AsyncSessionLocal() as db:
        country_result = await db.execute(
            select(Country).where(Country.code == "GE")
        )
        country = country_result.scalar_one_or_none()

        if not country:
            await _sync_id_sequence(db, "geo_countries")
            country = Country(
                name="Georgia",
                code="GE",
                name_i18n={
                    "en": "Georgia",
                    "ka": "საქართეთი",
                    "ru": "Грузия",
                },
            )
            db.add(country)
            await db.flush()
            print(f"Created country: Georgia (id={country.id})")
        else:
            print(f"Country already exists: id={country.id}, code={country.code}")

        region_result = await db.execute(
            select(Region).where(
                Region.country_id == country.id,
                Region.name == "Батуми",
            )
        )
        region = region_result.scalar_one_or_none()

        if not region:
            await _sync_id_sequence(db, "geo_regions")
            region = Region(
                country_id=country.id,
                name="Batumi",
                name_i18n={
                    "en": "Batumi",
                    "ka": "ბათუმი",
                    "ru": "Батуми",
                },
                type=None,
                default_lat=BATUMI_LAT,
                default_lng=BATUMI_LNG,
            )
            db.add(region)
            await db.flush()
            print(f"Created region: Batumi (id={region.id})")
        else:
            updated = False
            if region.default_lat is None:
                region.default_lat = BATUMI_LAT
                updated = True
            if region.default_lng is None:
                region.default_lng = BATUMI_LNG
                updated = True
            if updated:
                print(f"Updated map center for region id={region.id}")
            else:
                print(f"Region already exists: id={region.id}")

        await db.commit()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(seed_batumi_region())
