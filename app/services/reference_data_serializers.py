"""Serializers for localized reference data."""

from __future__ import annotations

from collections.abc import Callable

from app.db.models import Country, ProducerSKU, ProductCategory, Region, TemperatureMode
from app.schemas.country import CountryResponse
from app.schemas.producer_sku import ProducerSKUDetailResponse
from app.schemas.product_category import ProductCategoryResponse
from app.schemas.region import RegionDetailResponse, RegionListResponse
from app.schemas.temperature_mode import TemperatureModeResponse
from app.utils.i18n_fields import DEFAULT_LANG, resolve_i18n


def to_country_response(
    country: Country,
    lang: str = DEFAULT_LANG,
) -> CountryResponse:
    return CountryResponse(
        id=country.id,
        code=country.code,
        name=resolve_i18n(country.name_i18n, lang, fallback=country.name) or country.name,
        name_i18n=country.name_i18n,
    )


def to_region_list_response(
    region: Region,
    lang: str = DEFAULT_LANG,
) -> RegionListResponse:
    return RegionListResponse(
        id=region.id,
        name=resolve_i18n(region.name_i18n, lang, fallback=region.name) or region.name,
        name_i18n=region.name_i18n,
        type=region.type.value if region.type else None,
        default_lat=region.default_lat,
        default_lng=region.default_lng,
        country=to_country_response(region.country, lang),
    )


def to_region_detail_response(
    region: Region,
    *,
    lang: str = DEFAULT_LANG,
    distribution_centers: list,
    pricing_response,
    stats,
) -> RegionDetailResponse:
    return RegionDetailResponse(
        id=region.id,
        name=resolve_i18n(region.name_i18n, lang, fallback=region.name) or region.name,
        name_i18n=region.name_i18n,
        type=region.type.value if region.type else None,
        default_lat=region.default_lat,
        default_lng=region.default_lng,
        country=to_country_response(region.country, lang),
        distribution_centers=distribution_centers,
        pricing=pricing_response,
        stats=stats,
    )


def to_product_category_response(
    category: ProductCategory,
    lang: str = DEFAULT_LANG,
) -> ProductCategoryResponse:
    return ProductCategoryResponse(
        id=category.id,
        name=resolve_i18n(category.name_i18n, lang, fallback=category.name) or category.name,
        description=resolve_i18n(
            category.description_i18n,
            lang,
            fallback=category.description,
        ),
        name_i18n=category.name_i18n,
        description_i18n=category.description_i18n,
        is_active=category.is_active,
        sort_order=category.sort_order,
        cost_multiplier=float(category.cost_multiplier),
        slug=category.slug,
    )


def to_temperature_mode_response(
    mode: TemperatureMode,
    lang: str = DEFAULT_LANG,
) -> TemperatureModeResponse:
    return TemperatureModeResponse(
        id=mode.id,
        name=resolve_i18n(mode.name_i18n, lang, fallback=mode.name) or mode.name,
        description=resolve_i18n(
            mode.description_i18n,
            lang,
            fallback=mode.description,
        ),
        name_i18n=mode.name_i18n,
        description_i18n=mode.description_i18n,
        is_active=mode.is_active,
        sort_order=mode.sort_order,
        cost_multiplier=float(mode.cost_multiplier),
        slug=mode.slug,
        min_temperature=mode.min_temperature,
        max_temperature=mode.max_temperature,
    )


def to_producer_sku_detail_response(
    sku: ProducerSKU,
    lang: str = DEFAULT_LANG,
) -> ProducerSKUDetailResponse:
    response = ProducerSKUDetailResponse.model_validate(sku)
    return response.model_copy(
        update={
            "product_category": (
                to_product_category_response(sku.product_category, lang)
                if sku.product_category
                else None
            ),
            "temperature_mode": (
                to_temperature_mode_response(sku.temperature_mode, lang)
                if sku.temperature_mode
                else None
            ),
        }
    )


def add_reference_labels_to_lookup(
    lookup: dict[str, int],
    entity_id: int,
    *,
    name_i18n: dict[str, str] | None,
    legacy_name: str | None,
    slug: str | None,
    normalize: Callable[[str], str],
) -> None:
    """Register all localized labels for Excel/import text matching."""
    labels: list[str] = []
    if name_i18n:
        labels.extend(name_i18n.values())
    if legacy_name:
        labels.append(legacy_name)
    if slug:
        labels.append(slug)

    seen: set[str] = set()
    for label in labels:
        value = label.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        lookup[normalize(value)] = entity_id
        before_paren = value.split("(", 1)[0].strip()
        if before_paren and before_paren != value:
            lookup[normalize(before_paren)] = entity_id
