"""Unit tests for regions endpoints."""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.regions import (_get_region_stats, get_region,
                                          get_regions)
from app.db.models import Country, DistributionCenter, Region, RegionPricing
from app.db.models.enums import RegionType


@pytest.fixture
def fake_country():
    """Create fake country for testing."""
    return Country(id=1, name="Россия", code="RU")


@pytest.fixture
def fake_region(fake_country):
    """Create fake region for testing."""
    region = Region(
        id=1,
        name="Краснодарский край",
        type=RegionType.KRAI,
        country_id=1,
    )
    region.country = fake_country
    region.distribution_centers = []
    region.pricing = None
    return region


@pytest.fixture
def fake_regions(fake_country):
    """Create list of fake regions for testing."""
    region1 = Region(
        id=1,
        name="Краснодарский край",
        type=RegionType.KRAI,
        country_id=1,
    )
    region1.country = fake_country

    region2 = Region(
        id=2,
        name="Московская область",
        type=RegionType.OBLAST,
        country_id=1,
    )
    region2.country = fake_country

    return [region1, region2]


@pytest.fixture
def fake_distribution_centers():
    """Create fake distribution centers for testing."""
    return [
        DistributionCenter(
            id=1,
            region_id=1,
            name="РЦ Адлер",
            location="POINT(39.723098 43.585472)",
            address="село Казачий Брод, Краснофлотская улица, 27",
            is_active=True,
        ),
        DistributionCenter(
            id=2,
            region_id=1,
            name="РЦ Сочи",
            location="POINT(39.730678 43.585525)",
            address="Сочи, улица Энергетиков, 1Б",
            is_active=True,
        ),
    ]


@pytest.fixture
def fake_region_pricing():
    """Create fake region pricing for testing."""
    return RegionPricing(
        id=1,
        region_id=1,
        driver_hourly_rate=Decimal("500.00"),
        planned_work_hours=Decimal("8.00"),
        fuel_price_per_liter=Decimal("55.00"),
        fuel_consumption_per_100km=Decimal("12.00"),
        depreciation_coefficient=Decimal("0.15"),
        warehouse_processing_per_kg=Decimal("5.00"),
        service_fee_per_kg=Decimal("10.00"),
        delivery_point_cost=Decimal("150.00"),
        standard_trip_weight=Decimal("5000.00"),
        standard_box_length=60,
        standard_box_width=40,
        standard_box_height=40,
        standard_box_max_weight=Decimal("30.00"),
        min_points_for_discount=100,
        discount_step_points=50,
        initial_discount_percent=Decimal("5.00"),
        discount_step_percent=Decimal("5.00"),
    )


@pytest.mark.asyncio
async def test_get_regions_empty(mock_db_session):
    """Test getting regions when database is empty."""
    # Setup mock to return empty list
    mock_result = MagicMock()
    mock_result.unique().scalars().all.return_value = []
    mock_db_session.execute.return_value = mock_result

    # Call endpoint function
    result = await get_regions(db=mock_db_session)

    # Assertions
    assert result == []
    assert mock_db_session.execute.called


@pytest.mark.asyncio
async def test_get_regions_returns_list(mock_db_session, fake_regions):
    """Test getting all regions returns list."""
    # Setup mock to return fake regions
    mock_result = MagicMock()
    mock_result.unique().scalars().all.return_value = fake_regions
    mock_db_session.execute.return_value = mock_result

    # Call endpoint function
    result = await get_regions(db=mock_db_session)

    # Assertions
    assert len(result) == 2
    assert result[0].name == "Краснодарский край"
    assert result[0].type == RegionType.KRAI
    assert result[0].country.name == "Россия"
    assert result[1].name == "Московская область"
    assert mock_db_session.execute.called


@pytest.mark.asyncio
async def test_get_regions_with_country_filter(mock_db_session, fake_regions):
    """Test getting regions filtered by country_id."""
    # Setup mock
    mock_result = MagicMock()
    mock_result.unique().scalars().all.return_value = fake_regions
    mock_db_session.execute.return_value = mock_result

    # Call endpoint function with country filter
    result = await get_regions(db=mock_db_session, country_id=1)

    # Assertions
    assert len(result) == 2
    assert mock_db_session.execute.called


@pytest.mark.asyncio
async def test_get_region_by_id_success(
    mock_db_session, fake_region, fake_distribution_centers, fake_region_pricing
):
    """Test getting region by ID returns full information."""
    # Setup region with relationships
    fake_region.distribution_centers = fake_distribution_centers
    fake_region.pricing = fake_region_pricing

    # Setup mock for region query
    mock_region_result = MagicMock()
    mock_region_result.unique().scalar_one_or_none.return_value = fake_region

    # Setup mock for stats query (single query with all counts)
    mock_stats_row = MagicMock()
    mock_stats_row.dc_count = 2
    mock_stats_row.sectors_count = 45
    mock_stats_row.settlements_count = 123

    mock_stats_result = MagicMock()
    mock_stats_result.one.return_value = mock_stats_row

    # Two execute calls: first for region, second for stats
    mock_db_session.execute.side_effect = [mock_region_result, mock_stats_result]

    # Call endpoint function
    result = await get_region(region_id=1, db=mock_db_session)

    # Assertions
    assert result["id"] == 1
    assert result["name"] == "Краснодарский край"
    assert result["type"] == "край"
    assert result["country"].name == "Россия"
    assert len(result["distribution_centers"]) == 2
    assert result["distribution_centers"][0].name == "РЦ Адлер"
    assert result["pricing"] is not None
    assert result["pricing"].driver_hourly_rate == Decimal("500.00")
    assert result["stats"].distribution_centers_count == 2
    assert result["stats"].sectors_count == 45
    assert result["stats"].settlements_count == 123
    assert mock_db_session.execute.call_count == 2  # Region query + stats query


@pytest.mark.asyncio
async def test_get_region_without_pricing(mock_db_session, fake_region):
    """Test getting region without pricing returns null for pricing."""
    # Setup region without pricing
    fake_region.pricing = None

    # Setup mock for region query
    mock_region_result = MagicMock()
    mock_region_result.unique().scalar_one_or_none.return_value = fake_region

    # Setup mock for stats query (empty stats)
    mock_stats_row = MagicMock()
    mock_stats_row.dc_count = 0
    mock_stats_row.sectors_count = 0
    mock_stats_row.settlements_count = 0

    mock_stats_result = MagicMock()
    mock_stats_result.one.return_value = mock_stats_row

    # Two execute calls
    mock_db_session.execute.side_effect = [mock_region_result, mock_stats_result]

    # Call endpoint function
    result = await get_region(region_id=1, db=mock_db_session)

    # Assertions
    assert result["pricing"] is None
    assert result["stats"].distribution_centers_count == 0


@pytest.mark.asyncio
async def test_get_region_not_found(mock_db_session):
    """Test getting non-existent region raises HTTPException."""
    # Setup mock to return None (region not found)
    mock_result = MagicMock()
    mock_result.unique().scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    # Call endpoint function and expect exception
    with pytest.raises(HTTPException) as exc_info:
        await get_region(region_id=999, db=mock_db_session)

    # Assertions
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()
    assert "999" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_region_stats(mock_db_session):
    """Test getting region statistics with single query."""
    # Mock result with all counts in one row
    mock_row = MagicMock()
    mock_row.dc_count = 8
    mock_row.sectors_count = 45
    mock_row.settlements_count = 123

    mock_result = MagicMock()
    mock_result.one.return_value = mock_row
    mock_db_session.execute.return_value = mock_result

    # Call helper function
    stats = await _get_region_stats(db=mock_db_session, region_id=1)

    # Assertions
    assert stats.distribution_centers_count == 8
    assert stats.sectors_count == 45
    assert stats.settlements_count == 123
    assert mock_db_session.execute.call_count == 1  # Only one query!


@pytest.mark.asyncio
async def test_get_region_stats_empty(mock_db_session):
    """Test getting region statistics when region has no data."""
    # Mock result with None counts (no data)
    mock_row = MagicMock()
    mock_row.dc_count = None
    mock_row.sectors_count = None
    mock_row.settlements_count = None

    mock_result = MagicMock()
    mock_result.one.return_value = mock_row
    mock_db_session.execute.return_value = mock_result

    # Call helper function
    stats = await _get_region_stats(db=mock_db_session, region_id=1)

    # Assertions - should default to 0
    assert stats.distribution_centers_count == 0
    assert stats.sectors_count == 0
    assert stats.settlements_count == 0


@pytest.mark.asyncio
async def test_region_pricing_conversion(fake_region_pricing):
    """Test RegionPricing to RegionPricingResponse conversion."""
    from app.schemas.region import RegionPricingResponse

    # Convert pricing model to response schema
    pricing_response = RegionPricingResponse.from_pricing_model(fake_region_pricing)

    # Assertions
    assert pricing_response.driver_hourly_rate == Decimal("500.00")
    assert pricing_response.fuel_price_per_liter == Decimal("55.00")
    assert pricing_response.delivery_point_cost == Decimal("150.00")
    assert pricing_response.standard_box.length == 60
    assert pricing_response.standard_box.width == 40
    assert pricing_response.standard_box.max_weight == Decimal("30.00")
    assert pricing_response.discount.min_points == 100
    assert pricing_response.discount.step_points == 50
    assert pricing_response.discount.initial_percent == Decimal("5.00")
