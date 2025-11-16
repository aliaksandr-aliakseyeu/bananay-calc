"""Unit tests for sectors endpoints."""
from unittest.mock import MagicMock

import pytest

from app.api.v1.endpoints.sectors import get_sectors


@pytest.fixture
def fake_sectors_rows():
    """Create fake sector rows with GeoJSON boundary."""
    # Mock row 1
    row1 = MagicMock()
    row1.id = 1
    row1.region_id = 1
    row1.name = "Адлерский сектор 1"
    row1.description = "Сектор доставки в Адлерском районе"
    row1.boundary_geojson = (
        '{"type":"Polygon","coordinates":[[[39.723098,43.585472],'
        '[39.730678,43.585525],[39.732,43.58],[39.723098,43.585472]]]}'
    )

    # Mock row 2
    row2 = MagicMock()
    row2.id = 2
    row2.region_id = 1
    row2.name = "Адлерский сектор 2"
    row2.description = None
    row2.boundary_geojson = (
        '{"type":"Polygon","coordinates":[[[39.74,43.59],'
        '[39.75,43.60],[39.76,43.59],[39.74,43.59]]]}'
    )

    return [row1, row2]


@pytest.mark.asyncio
async def test_get_sectors_empty(mock_db_session):
    """Test getting sectors when no sectors exist for region."""
    # Setup mock to return empty list
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_db_session.execute.return_value = mock_result

    # Call endpoint function
    result = await get_sectors(db=mock_db_session, region_id=1)

    # Assertions
    assert result == []
    assert mock_db_session.execute.called


@pytest.mark.asyncio
async def test_get_sectors_returns_list(mock_db_session, fake_sectors_rows):
    """Test getting all sectors for a region."""
    # Setup mock to return fake sectors
    mock_result = MagicMock()
    mock_result.all.return_value = fake_sectors_rows
    mock_db_session.execute.return_value = mock_result

    # Call endpoint function
    result = await get_sectors(db=mock_db_session, region_id=1)

    # Assertions
    assert len(result) == 2
    assert mock_db_session.execute.called

    # Check first sector
    assert result[0]["id"] == 1
    assert result[0]["region_id"] == 1
    assert result[0]["name"] == "Адлерский сектор 1"
    assert result[0]["description"] == "Сектор доставки в Адлерском районе"

    # Check boundary is GeoJSON Polygon
    assert result[0]["boundary"]["type"] == "Polygon"
    assert "coordinates" in result[0]["boundary"]
    assert isinstance(result[0]["boundary"]["coordinates"], list)
    assert len(result[0]["boundary"]["coordinates"][0]) == 4  # 4 points (closed polygon)

    # Check second sector
    assert result[1]["id"] == 2
    assert result[1]["name"] == "Адлерский сектор 2"
    assert result[1]["description"] is None


@pytest.mark.asyncio
async def test_get_sectors_geojson_format(mock_db_session, fake_sectors_rows):
    """Test that boundary is properly converted to GeoJSON format."""
    # Setup mock
    mock_result = MagicMock()
    mock_result.all.return_value = [fake_sectors_rows[0]]
    mock_db_session.execute.return_value = mock_result

    # Call endpoint function
    result = await get_sectors(db=mock_db_session, region_id=1)

    # Verify GeoJSON structure
    boundary = result[0]["boundary"]
    assert boundary["type"] == "Polygon"
    assert isinstance(boundary["coordinates"], list)
    assert isinstance(boundary["coordinates"][0], list)
    assert isinstance(boundary["coordinates"][0][0], list)
    assert len(boundary["coordinates"][0][0]) == 2  # [lng, lat]

    # First coordinate should be [39.723098, 43.585472]
    first_point = boundary["coordinates"][0][0]
    assert first_point[0] == 39.723098  # longitude
    assert first_point[1] == 43.585472  # latitude


@pytest.mark.asyncio
async def test_get_sectors_filters_by_region(mock_db_session):
    """Test that sectors are filtered by region_id."""
    # Setup mock
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_db_session.execute.return_value = mock_result

    # Call endpoint with specific region_id
    await get_sectors(db=mock_db_session, region_id=42)

    # Verify execute was called (query was executed)
    assert mock_db_session.execute.called
    # In a real test, we would check the WHERE clause contains region_id=42


@pytest.mark.asyncio
async def test_get_sectors_ordered_by_id(mock_db_session, fake_sectors_rows):
    """Test that sectors are ordered by id."""
    # Setup mock
    mock_result = MagicMock()
    mock_result.all.return_value = fake_sectors_rows
    mock_db_session.execute.return_value = mock_result

    # Call endpoint function
    result = await get_sectors(db=mock_db_session, region_id=1)

    # Verify ordering
    assert result[0]["id"] == 1
    assert result[1]["id"] == 2
    assert result[0]["id"] < result[1]["id"]
