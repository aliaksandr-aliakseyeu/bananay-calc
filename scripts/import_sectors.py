"""
Скрипт импорта секторов из GeoJSON файла в базу данных.

Использование:
    poetry run python scripts/import_sectors.py
"""
import asyncio
import io
import json
import sys
from pathlib import Path

from geoalchemy2.shape import from_shape
from shapely.geometry import shape
from sqlalchemy import text

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import engine  # noqa: E402
from app.db.models import Sector  # noqa: E402


async def import_sectors(geojson_path: str, region_id: int = 1):
    """
    Импорт секторов из GeoJSON файла.

    Args:
        geojson_path: Путь к GeoJSON файлу
        region_id: ID региона для привязки секторов (по умолчанию 1 - Краснодарский край)
    """
    with open(geojson_path, 'r', encoding='utf-8') as f:
        geojson_data = json.load(f)

    if geojson_data['type'] != 'FeatureCollection':
        raise ValueError(f"Expected FeatureCollection, got {geojson_data['type']}")

    features = geojson_data['features']
    print(f'Найдено {len(features)} полигонов в GeoJSON файле')

    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT name FROM regions WHERE id = :region_id"),
            {"region_id": region_id}
        )
        region_row = result.fetchone()

        if not region_row:
            raise ValueError(f'Регион с ID {region_id} не найден в базе данных')

        print(f'Регион найден: {region_row[0]} (ID: {region_id})')

        imported_count = 0
        for idx, feature in enumerate(features, 1):
            if feature['type'] != 'Feature':
                print(f'[!] Пропускаем feature #{idx}: тип {feature["type"]}')
                continue

            geometry = feature['geometry']
            if geometry['type'] != 'Polygon':
                print(f'[!] Пропускаем feature #{idx}: геометрия {geometry["type"]}')
                continue

            polygon = shape(geometry)

            name = feature.get('properties', {}).get('name')
            description = feature.get('properties', {}).get('description')

            await conn.execute(
                Sector.__table__.insert().values(
                    region_id=region_id,
                    name=name,
                    description=description,
                    boundary=from_shape(polygon, srid=4326)
                )
            )

            imported_count += 1
            name_str = f" '{name}'" if name else ""
            print(f'  ✓ Сектор #{idx}{name_str} импортирован')

        print(f'\n✅ Успешно импортировано секторов: {imported_count}/{len(features)}')

    await engine.dispose()


async def main():
    """Главная функция."""
    geojson_path = Path(__file__).parent.parent / 'сектора.json'

    if not geojson_path.exists():
        print(f'❌ Файл не найден: {geojson_path}')
        sys.exit(1)

    print(f'📂 Файл найден: {geojson_path.name}')
    print('🚀 Начинаю импорт секторов...\n')

    try:
        await import_sectors(str(geojson_path), region_id=1)
    except Exception as e:
        print(f'\n❌ Ошибка импорта: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
