"""
Скрипт для добавления распределительных центров с геокодированием через Яндекс API.

Использование:
    poetry run python scripts/seed_distribution_centers.py

Требования:
    - В .env файле должен быть YANDEX_API_KEY
"""
import asyncio
import sys
from pathlib import Path

import httpx
from sqlalchemy import select, text

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings  # noqa: E402
from app.db.base import engine  # noqa: E402
from app.db.models import DistributionCenter  # noqa: E402

YANDEX_API_KEY = settings.YANDEX_API_KEY
YANDEX_GEOCODER_URL = "https://geocode-maps.yandex.ru/1.x/"

# Данные распределительных центров
DISTRIBUTION_CENTERS = [
    {
        "address": "Краснодарский край, городской округ Сочи, село Казачий Брод, Краснофлотская улица, 27",
        "name": "РЦ Казачий Брод",
        "district": "Адлерский"
    },
    {
        "address": "Краснодарский край, Сочи, улица Энергетиков, 1Б",
        "name": "РЦ Энергетиков 1Б",
        "district": "Адлерский"
    },
    {
        "address": "Краснодарский край, городской округ Сочи, село Орёл-Изумруд, Банановая улица, 10И",
        "name": "РЦ Орёл-Изумруд",
        "district": "Адлерский"
    },
    {
        "address": "Краснодарский край, Сочи, улица Энергетиков, 3",
        "name": "РЦ Энергетиков 3",
        "district": "Адлерский"
    },
    {
        "address": "Краснодарский край, Сочи, Сухумское шоссе, 37А",
        "name": "РЦ Сухумское шоссе",
        "district": "Хостинский"
    },
    {
        "address": "Краснодарский край, Сочи, жилой район Хоста, Самшитовая улица, 45",
        "name": "РЦ Хоста",
        "district": "Хостинский"
    },
    {
        "address": "Краснодарский край, Сочи, Краснодонская улица, 40",
        "name": "РЦ Краснодонская",
        "district": "Центральный"
    },
    {
        "address": "Краснодарский край, Сочи, Виноградный переулок, 2А",
        "name": "РЦ Виноградный",
        "district": "Центральный"
    }
]


async def geocode_address(address: str) -> tuple[float, float] | None:
    """
    Геокодирование адреса через Яндекс API.

    Args:
        address: Адрес для геокодирования

    Returns:
        (latitude, longitude) или None если не найдено
    """
    if not YANDEX_API_KEY:
        raise ValueError("YANDEX_API_KEY not found in .env file")

    params = {
        "apikey": YANDEX_API_KEY,
        "geocode": address,
        "format": "json",
        "results": 1
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(YANDEX_GEOCODER_URL, params=params)
            response.raise_for_status()

            data = response.json()
            geo_object = data["response"]["GeoObjectCollection"]["featureMember"]

            if not geo_object:
                print(f"  ! Address not found: {address}")
                return None

            pos = geo_object[0]["GeoObject"]["Point"]["pos"]
            lng, lat = map(float, pos.split())

            return (lat, lng)

        except httpx.HTTPError as e:
            print(f"  ! HTTP error for {address}: {e}")
            return None
        except (KeyError, IndexError, ValueError) as e:
            print(f"  ! Parse error for {address}: {e}")
            return None


async def seed_distribution_centers():
    """Добавить распределительные центры в базу."""
    print("=" * 70)
    print("SEED DISTRIBUTION CENTERS")
    print("=" * 70)

    if not YANDEX_API_KEY:
        print("\n! ERROR: YANDEX_API_KEY not found in .env file")
        print("  Please add YANDEX_API_KEY=your_key to .env")
        sys.exit(1)

    print("\n+ Using Yandex Geocoder API")
    print(f"+ Total centers to add: {len(DISTRIBUTION_CENTERS)}\n")

    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT id FROM regions WHERE name LIKE '%Краснодарск%' LIMIT 1")
        )
        region_row = result.fetchone()

        if not region_row:
            print("\n! ERROR: Krasnodarsky Krai region not found in database")
            sys.exit(1)

        region_id = region_row[0]
        print(f"+ Found region_id: {region_id}\n")

    success_count = 0
    failed_count = 0

    for idx, center_data in enumerate(DISTRIBUTION_CENTERS, 1):
        print(f"[{idx}/{len(DISTRIBUTION_CENTERS)}] {center_data['name']}")
        print(f"  Address: {center_data['address']}")
        print(f"  District: {center_data['district']}")

        coords = await geocode_address(center_data['address'])

        if not coords:
            print("  X Failed to geocode\n")
            failed_count += 1
            continue

        lat, lng = coords
        print(f"  Coordinates: {lat:.6f}, {lng:.6f}")

        try:
            async with engine.begin() as conn:
                result = await conn.execute(
                    select(DistributionCenter.id).where(
                        DistributionCenter.name == center_data['name']
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    print(f"  ~ Already exists (id={existing})")
                else:
                    # Создаем новый РЦ
                    await conn.execute(
                        text("""
                            INSERT INTO distribution_centers
                            (region_id, name, location, address, is_active)
                            VALUES
                            (:region_id, :name, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), :address, :is_active)
                        """),
                        {
                            "region_id": region_id,
                            "name": center_data['name'],
                            "lng": lng,
                            "lat": lat,
                            "address": center_data['address'],
                            "is_active": True
                        }
                    )
                    print("  + Created successfully")
                    success_count += 1

        except Exception as e:
            print(f"  X Database error: {e}")
            failed_count += 1

        print()

        if idx < len(DISTRIBUTION_CENTERS):
            await asyncio.sleep(0.2)

    await engine.dispose()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total centers: {len(DISTRIBUTION_CENTERS)}")
    print(f"Successfully created: {success_count}")
    print(f"Failed: {failed_count}")
    print(f"Already existed: {len(DISTRIBUTION_CENTERS) - success_count - failed_count}")
    print("=" * 70)


if __name__ == '__main__':
    asyncio.run(seed_distribution_centers())
