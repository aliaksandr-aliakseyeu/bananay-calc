"""
Import Batumi delivery points from Yandex Excel export.

Usage:
    poetry run python scripts/import_batumi_delivery_points.py --dry-run --limit 20
    poetry run python scripts/import_batumi_delivery_points.py --file "C:/path/Organizatsii_Batumi.xlsx" --region-id 2
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import importlib.util
import io
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from geoalchemy2.functions import ST_GeomFromGeoJSON
from openpyxl import load_workbook
from sqlalchemy import select, text
from tqdm import tqdm

_SCRIPTS_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _SCRIPTS_DIR.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

from app.db.base import AsyncSessionLocal, engine
from app.db.models import Settlement, Tag, delivery_point_tags
from app.db.models.delivery_point import DeliveryPoint
from app.db.models.enums import SettlementType
from app.services.nominatim_geocoding_service import NominatimGeocodingService
from app.utils.schedule_i18n import translate_schedule_to_i18n
from app.utils.slugify import slugify

_batumi_name_utils_path = _SCRIPTS_DIR / "batumi_name_utils.py"
_batumi_name_utils_spec = importlib.util.spec_from_file_location(
    "batumi_name_utils",
    _batumi_name_utils_path,
)
if _batumi_name_utils_spec is None or _batumi_name_utils_spec.loader is None:
    raise ImportError(f"Cannot load batumi_name_utils from {_batumi_name_utils_path}")
_batumi_name_utils = importlib.util.module_from_spec(_batumi_name_utils_spec)
_batumi_name_utils_spec.loader.exec_module(_batumi_name_utils)
NameScript = _batumi_name_utils.NameScript
classify_name = _batumi_name_utils.classify_name
resolve_fallback_name = _batumi_name_utils.resolve_fallback_name

DEFAULT_EXCEL = Path.home() / "Desktop" / "Organizatsii_Batumi.xlsx"
RUBRICS_PATH = Path(__file__).parent / "data" / "batumi_rubrics_en.json"
BATUMI_LAT = 41.6168
BATUMI_LNG = 41.6367
SETTLEMENT_NAME = "Batumi"
BATCH_SIZE = 50
SYNC_SEQUENCE_TABLES = ("geo_settlements", "geo_tags", "geo_delivery_points")

EXCEL_COLUMNS = [
    "Ссылка",
    "Название",
    "Телефон",
    "Адрес",
    "Рейтинг",
    "Оценки",
    "Сайт",
    "WhatsApp",
    "VK",
    "ТГ",
    "Viber",
    "Широта",
    "Долгота",
    "Город",
    "Рубрика",
    "Время работы",
    "Как добраться",
]


@dataclass
class ImportStats:
    total_rows: int = 0
    imported: int = 0
    russian_skipped: int = 0
    failed: int = 0
    dry_run_would_import: int = 0
    failures_by_reason: dict[str, int] = field(default_factory=lambda: defaultdict(int))


def load_rubrics() -> dict[str, str]:
    with RUBRICS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def safe_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value).strip() or None


YANDEX_LINK_RE = re.compile(r"^https?://(?:[a-z0-9-]+\.)*yandex\.", re.IGNORECASE)


def sanitize_external_link(value: str | None) -> str | None:
    if not value:
        return None
    if YANDEX_LINK_RE.match(value) or value.lower().startswith("yandex"):
        return None
    return value


def row_to_dict(headers: list[str], values: tuple[Any, ...]) -> dict[str, Any]:
    return {header: values[idx] if idx < len(values) else None for idx, header in enumerate(headers)}


async def sync_sequences(db) -> None:
    """Align serial sequences with current max ids (avoids duplicate PK on insert)."""
    for table_name in SYNC_SEQUENCE_TABLES:
        await db.execute(
            text(
                f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), "
                f"GREATEST(COALESCE((SELECT MAX(id) FROM {table_name}), 0), 1), true)"
            )
        )


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def resolve_name(
    original_name: str,
    script: NameScript,
    geocoder: NominatimGeocodingService,
    lat: float,
    lng: float,
) -> str | None:
    search_query = f"{original_name} Batumi, Georgia"
    english_name = geocoder.search_place_name(
        search_query,
        country_code="ge",
        lang="en",
        lat=lat,
        lng=lng,
    )
    if english_name:
        return english_name
    return resolve_fallback_name(original_name, script)


async def get_or_create_settlement(db, region_id: int, dry_run: bool) -> int | None:
    result = await db.execute(
        select(Settlement.id).where(
            Settlement.region_id == region_id,
            Settlement.name == SETTLEMENT_NAME,
        )
    )
    settlement_id = result.scalar_one_or_none()
    if settlement_id:
        return settlement_id

    if dry_run:
        return -1

    location_geojson = json.dumps(
        {"type": "Point", "coordinates": [BATUMI_LNG, BATUMI_LAT]}
    )
    settlement = Settlement(
        region_id=region_id,
        name=SETTLEMENT_NAME,
        type=SettlementType.GOROD,
        location=ST_GeomFromGeoJSON(location_geojson),
    )
    db.add(settlement)
    await db.flush()
    return settlement.id


async def get_or_create_tag(db, english_name: str, dry_run: bool) -> int | None:
    slug = slugify(english_name)
    result = await db.execute(
        text(
            "SELECT id FROM geo_tags "
            "WHERE LOWER(name) = LOWER(:name) OR slug = :slug"
        ),
        {"name": english_name, "slug": slug},
    )
    tag_id = result.scalar_one_or_none()
    if tag_id:
        return tag_id

    if dry_run:
        return -1

    tag = Tag(name=english_name, slug=slugify(english_name))
    db.add(tag)
    await db.flush()
    return tag.id


async def insert_delivery_point(
    db,
    *,
    settlement_id: int,
    name: str,
    rubric_en: str,
    address: str,
    lat: float,
    lng: float,
    phone: str | None,
    schedule: str | None,
    landmark: str | None,
    title: str | None,
    tag_id: int,
) -> None:
    location_geojson = json.dumps({"type": "Point", "coordinates": [lng, lat]})
    schedule_i18n = translate_schedule_to_i18n(schedule) if schedule else None
    point = DeliveryPoint(
        settlement_id=settlement_id,
        name=name,
        type=rubric_en,
        title=title,
        address=address,
        landmark=landmark,
        location=ST_GeomFromGeoJSON(location_geojson),
        phone=phone,
        schedule_i18n=schedule_i18n,
        is_active=True,
    )
    db.add(point)
    await db.flush()

    await db.execute(
        delivery_point_tags.insert().values(
            delivery_point_id=point.id,
            tag_id=tag_id,
        )
    )


def process_row(
    row_number: int,
    row_data: dict[str, Any],
    rubrics: dict[str, str],
    geocoder: NominatimGeocodingService,
) -> tuple[str | None, dict[str, Any] | None, str | None]:
    """
    Process one Excel row.

    Returns:
        (outcome, payload, reason)
        outcome: 'russian' | 'failed' | 'import'
        payload: dict with resolved fields for import
        reason: failure/skip reason
    """
    original_name = safe_str(row_data.get("Название"))
    script = classify_name(original_name)

    if script == NameScript.EMPTY:
        return "failed", None, "empty_name"

    if script == NameScript.RUSSIAN:
        return "russian", None, "russian_name"

    rubric_ru = safe_str(row_data.get("Рубрика"))
    if not rubric_ru:
        return "failed", None, "missing_rubric"

    rubric_en = rubrics.get(rubric_ru)
    if not rubric_en:
        return "failed", None, "unknown_rubric"

    lat = row_data.get("Широта")
    lng = row_data.get("Долгота")
    if lat is None or lng is None:
        return "failed", None, "missing_coordinates"

    try:
        lat_f = float(lat)
        lng_f = float(lng)
    except (TypeError, ValueError):
        return "failed", None, "invalid_coordinates"

    address = geocoder.reverse_address(lat_f, lng_f, lang="en")
    if not address:
        return "failed", None, "geocode_failed"

    name = resolve_name(original_name, script, geocoder, lat_f, lng_f)
    if not name:
        return "failed", None, "no_resolvable_name"

    payload = {
        "row_number": row_number,
        "name": name,
        "rubric_en": rubric_en,
        "address": address,
        "lat": lat_f,
        "lng": lng_f,
        "phone": safe_str(row_data.get("Телефон")),
        "schedule": safe_str(row_data.get("Время работы")),
        "landmark": safe_str(row_data.get("Как добраться")),
        "title": sanitize_external_link(safe_str(row_data.get("Ссылка"))),
        "original_name": original_name,
        "source_row": {col: row_data.get(col) for col in EXCEL_COLUMNS},
    }
    return "import", payload, None


async def import_batumi_delivery_points(
    excel_path: Path,
    region_id: int,
    output_dir: Path,
    dry_run: bool,
    limit: int | None,
) -> ImportStats:
    stats = ImportStats()
    rubrics = load_rubrics()
    geocoder = NominatimGeocodingService()

    print(f"Opening file: {excel_path.name}")
    wb = load_workbook(excel_path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise ValueError("Excel file is empty")

    headers = [str(h) if h is not None else "" for h in rows[0]]
    data_rows = rows[1:]
    if limit is not None:
        data_rows = data_rows[:limit]

    stats.total_rows = len(data_rows)
    russian_rows: list[dict[str, Any]] = []
    failed_rows: list[dict[str, Any]] = []
    import_queue: list[dict[str, Any]] = []

    csv_fieldnames = ["row_number", "reason"] + EXCEL_COLUMNS

    print(f"Rows to process: {stats.total_rows}")
    if dry_run:
        print("Mode: DRY RUN (no database writes — remove --dry-run to import)")
    else:
        print("Mode: IMPORT (will write to database)")
    print(f"Output dir: {output_dir}\n")

    async with engine.connect() as conn:
        region_result = await conn.execute(
            text("SELECT name FROM geo_regions WHERE id = :region_id"),
            {"region_id": region_id},
        )
        region_row = region_result.fetchone()
        if not region_row:
            raise ValueError(f"Region with id {region_id} not found")
        print(f"Region: {region_row[0]} (id={region_id})\n")

    for row_idx, values in enumerate(tqdm(data_rows, desc="Processing", unit="row"), start=2):
        row_number = row_idx
        row_data = row_to_dict(headers, values)
        outcome, payload, reason = process_row(row_number, row_data, rubrics, geocoder)

        if outcome == "russian":
            stats.russian_skipped += 1
            russian_rows.append({
                "row_number": row_number,
                "reason": reason,
                **{col: row_data.get(col) for col in EXCEL_COLUMNS},
            })
            continue

        if outcome == "failed":
            stats.failed += 1
            stats.failures_by_reason[reason or "unknown"] += 1
            failed_rows.append({
                "row_number": row_number,
                "reason": reason,
                **{col: row_data.get(col) for col in EXCEL_COLUMNS},
            })
            continue

        if payload:
            import_queue.append(payload)

    geocoder.flush_cache()

    write_csv(output_dir / "russian_names.csv", russian_rows, csv_fieldnames)

    if import_queue:
        async with AsyncSessionLocal() as db:
            if not dry_run:
                await sync_sequences(db)

            settlement_id = await get_or_create_settlement(db, region_id, dry_run)
            if settlement_id is None:
                raise RuntimeError("Failed to resolve settlement id")

            for item in tqdm(import_queue, desc="DB insert", unit="row"):
                try:
                    if dry_run:
                        stats.dry_run_would_import += 1
                        continue

                    tag_id = await get_or_create_tag(db, item["rubric_en"], dry_run=False)
                    if tag_id is None:
                        raise RuntimeError("Failed to resolve tag id")

                    await insert_delivery_point(
                        db,
                        settlement_id=settlement_id,
                        name=item["name"],
                        rubric_en=item["rubric_en"],
                        address=item["address"],
                        lat=item["lat"],
                        lng=item["lng"],
                        phone=item["phone"],
                        schedule=item["schedule"],
                        landmark=item["landmark"],
                        title=item["title"],
                        tag_id=tag_id,
                    )
                    stats.imported += 1
                except Exception as exc:
                    stats.failed += 1
                    stats.failures_by_reason["db_error"] += 1
                    source = item.get("source_row", {})
                    failed_rows.append({
                        "row_number": item["row_number"],
                        "reason": f"db_error: {exc}",
                        **source,
                    })
                    await db.rollback()
                    if not dry_run:
                        await sync_sequences(db)
                        settlement_id = await get_or_create_settlement(db, region_id, dry_run=False)

            if not dry_run:
                await db.commit()

    write_csv(output_dir / "failed_rows.csv", failed_rows, csv_fieldnames)

    await engine.dispose()
    print_summary(stats, dry_run, len(russian_rows), len(failed_rows), len(import_queue))
    return stats


def print_summary(
    stats: ImportStats,
    dry_run: bool,
    russian_count: int,
    failed_count: int,
    import_queue_count: int,
) -> None:
    print(f"\n{'=' * 70}")
    print("IMPORT SUMMARY")
    print(f"{'=' * 70}")
    print(f"Total rows processed:     {stats.total_rows}")
    print(f"Russian names (skipped):  {russian_count}")
    print(f"Ready for import:         {import_queue_count}")
    if dry_run:
        print(f"Would import:             {stats.dry_run_would_import}")
    else:
        print(f"Imported to DB:           {stats.imported}")
    print(f"Failed / skipped other:   {failed_count}")
    if stats.failures_by_reason:
        print("\nFailures by reason:")
        for reason, count in sorted(stats.failures_by_reason.items(), key=lambda x: -x[1]):
            print(f"  {reason}: {count}")
    print(f"{'=' * 70}\n")


async def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    parser = argparse.ArgumentParser(description="Import Batumi delivery points from Yandex Excel")
    parser.add_argument("--file", type=Path, default=DEFAULT_EXCEL, help="Path to Excel file")
    parser.add_argument("--region-id", type=int, default=2, help="Region ID (Batumi)")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to database")
    parser.add_argument("--limit", type=int, default=None, help="Process only first N rows")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for CSV reports",
    )
    args = parser.parse_args()

    if not args.file.exists():
        print(f"File not found: {args.file}")
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (Path(__file__).parent / "output" / f"batumi_import_{timestamp}")

    try:
        await import_batumi_delivery_points(
            excel_path=args.file,
            region_id=args.region_id,
            output_dir=output_dir,
            dry_run=args.dry_run,
            limit=args.limit,
        )
    except Exception as exc:
        print(f"Critical error: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
