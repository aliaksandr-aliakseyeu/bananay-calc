"""
Backfill schedule_i18n for delivery points in Batumi region only.

Processes in small patches (default 10) with a live progress bar.

Usage:
    docker exec bananay_calc_api python scripts/backfill_schedule_i18n.py
    docker exec bananay_calc_api python scripts/backfill_schedule_i18n.py --region-id 2
    docker exec bananay_calc_api python scripts/backfill_schedule_i18n.py --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import io
import json
import sys
import time
from pathlib import Path

from sqlalchemy import func, or_, select, text
from tqdm import tqdm

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import AsyncSessionLocal
from app.db.models.delivery_point import DeliveryPoint
from app.db.models.settlement import Settlement
from app.utils.schedule_i18n import translate_schedule_to_i18n

DEFAULT_BATCH_SIZE = 10
DEFAULT_BATUMI_REGION_ID = 2


def pending_filters(region_id: int, *, retranslate_phrases: bool):
    base = (
        DeliveryPoint.settlement_id == Settlement.id,
        Settlement.region_id == region_id,
        DeliveryPoint.schedule.is_not(None),
        DeliveryPoint.schedule != "",
    )
    if retranslate_phrases:
        return base + (
            or_(
                DeliveryPoint.schedule_i18n.is_(None),
                DeliveryPoint.schedule == "График работы не указан",
            ),
        )
    return base + (DeliveryPoint.schedule_i18n.is_(None),)


async def resolve_region_name(region_id: int) -> str:
    async with AsyncSessionLocal() as db:
        row = await db.execute(
            text("SELECT name FROM geo_regions WHERE id = :id"),
            {"id": region_id},
        )
        name = row.scalar_one_or_none()
        if name is None:
            raise SystemExit(f"Region id={region_id} not found")
        return name


async def count_pending(region_id: int, *, retranslate_phrases: bool) -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(func.count())
            .select_from(DeliveryPoint)
            .join(Settlement, DeliveryPoint.settlement_id == Settlement.id)
            .where(*pending_filters(region_id, retranslate_phrases=retranslate_phrases))
        )
        return int(result.scalar_one())


async def fetch_batch(region_id: int, limit: int, *, retranslate_phrases: bool) -> list[tuple[int, str]]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DeliveryPoint.id, DeliveryPoint.schedule)
            .join(Settlement, DeliveryPoint.settlement_id == Settlement.id)
            .where(*pending_filters(region_id, retranslate_phrases=retranslate_phrases))
            .order_by(DeliveryPoint.id)
            .limit(limit)
        )
        return [(row.id, row.schedule) for row in result.all() if row.schedule and row.schedule.strip()]


async def apply_batch(chunk: list[tuple[int, str]], region_id: int) -> int:
    updated = 0
    async with AsyncSessionLocal() as db:
        for point_id, schedule in chunk:
            i18n = translate_schedule_to_i18n(schedule)
            if not i18n:
                continue

            result = await db.execute(
                text(
                    """
                    UPDATE geo_delivery_points dp
                    SET schedule_i18n = CAST(:schedule_i18n AS jsonb),
                        schedule = :schedule_en
                    FROM geo_settlements s
                    WHERE dp.id = :id
                      AND dp.settlement_id = s.id
                      AND s.region_id = :region_id
                    """
                ),
                {
                    "id": point_id,
                    "region_id": region_id,
                    "schedule_i18n": json.dumps(i18n, ensure_ascii=False),
                    "schedule_en": i18n["en"],
                },
            )
            if result.rowcount:
                updated += 1

        await db.commit()
    return updated


async def backfill(
    *,
    region_id: int,
    batch_size: int,
    dry_run: bool,
    with_total: bool,
    retranslate_phrases: bool,
) -> None:
    region_name = await resolve_region_name(region_id)
    mode = " + retranslate known phrases" if retranslate_phrases else ""
    print(
        f"Backfill schedule_i18n — region {region_name} (id={region_id}), "
        f"patch size {batch_size}{mode}",
        flush=True,
    )

    total: int | None = None
    if with_total:
        print("Counting rows...", flush=True)
        total = await count_pending(region_id, retranslate_phrases=retranslate_phrases)
        print(f"Pending in region: {total}", flush=True)
        if total == 0:
            print("Nothing to do.")
            return
    else:
        print("Skipping COUNT — progress bar starts immediately.", flush=True)

    if dry_run:
        sample = await fetch_batch(region_id, min(batch_size, 5), retranslate_phrases=retranslate_phrases)
        for point_id, schedule in sample:
            i18n = translate_schedule_to_i18n(schedule)
            print(f"  id={point_id}: {schedule!r} -> {i18n}", flush=True)
        if not sample:
            print("No rows to backfill in this region.")
        return

    processed = 0
    updated = 0
    patch_no = 0
    started = time.monotonic()

    bar = tqdm(
        total=total,
        desc="schedule_i18n",
        unit="row",
        file=sys.stderr,
        mininterval=0.3,
        dynamic_ncols=True,
    )

    try:
        while True:
            patch_no += 1
            bar.set_postfix(patch=patch_no, refresh=False)

            chunk = await fetch_batch(region_id, batch_size, retranslate_phrases=retranslate_phrases)
            if not chunk:
                break

            patch_updated = await apply_batch(chunk, region_id)
            processed += len(chunk)
            updated += patch_updated
            bar.update(len(chunk))

            elapsed = max(time.monotonic() - started, 0.001)
            rate = processed / elapsed
            print(
                f"patch {patch_no}: +{len(chunk)} rows "
                f"({patch_updated} updated) | total {processed} | {rate:.1f} row/s",
                flush=True,
            )
    finally:
        bar.close()

    print(f"Done. Processed {processed}, updated {updated} points in region {region_id}.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill schedule_i18n for one region (default: Batumi)")
    parser.add_argument(
        "--region-id",
        type=int,
        default=DEFAULT_BATUMI_REGION_ID,
        help=f"Region ID (default: {DEFAULT_BATUMI_REGION_ID} = Batumi)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Rows per DB patch (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--with-total",
        action="store_true",
        help="Run COUNT first to show %% on progress bar",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument(
        "--retranslate-phrases",
        action="store_true",
        help='Re-translate rows still showing "График работы не указан" (and other known phrases)',
    )
    args = parser.parse_args()

    if args.batch_size < 1:
        parser.error("--batch-size must be >= 1")

    asyncio.run(
        backfill(
            region_id=args.region_id,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
            with_total=args.with_total,
            retranslate_phrases=args.retranslate_phrases,
        )
    )


if __name__ == "__main__":
    main()
