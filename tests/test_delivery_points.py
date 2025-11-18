"""Unit tests for delivery points endpoints."""
from unittest.mock import MagicMock

import pytest

from app.api.v1.endpoints.delivery_points import search_delivery_points
from app.schemas.delivery_point import BoundingBox, DeliveryPointSearchRequest


@pytest.fixture
def fake_delivery_points_rows():
    """Create fake delivery point rows with GeoJSON location."""
    row1 = MagicMock()
    row1.id = 1
    row1.name = "Магазин Пятёрочка"
    row1.type = "Магазин"
    row1.title = "Пятёрочка на Краснофлотской"
    row1.address = "село Казачий Брод, Краснофлотская улица, 27"
    row1.address_comment = "Вход со стороны парковки"
    row1.landmark = "Рядом с автобусной остановкой"
    row1.location_geojson = '{"type":"Point","coordinates":[39.723098,43.585472]}'
    row1.phone = "+7 (862) 123-45-67"
    row1.mobile = "+7 (999) 123-45-67"
    row1.email = "shop@example.com"
    row1.schedule = "Пн-Вс: 08:00-22:00"
    row1.is_active = True

    row2 = MagicMock()
    row2.id = 2
    row2.name = "Аптека 36.6"
    row2.type = "Аптека"
    row2.title = None
    row2.address = "Сочи, улица Энергетиков, 1Б"
    row2.address_comment = None
    row2.landmark = None
    row2.location_geojson = '{"type":"Point","coordinates":[39.730678,43.585525]}'
    row2.phone = "+7 (862) 987-65-43"
    row2.mobile = None
    row2.email = None
    row2.schedule = "Пн-Пт: 09:00-20:00"
    row2.is_active = True

    return [row1, row2]


@pytest.mark.asyncio
async def test_search_delivery_points_empty(mock_db_session):
    """Test search when no delivery points match filters."""
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_db_session.execute.return_value = mock_result

    filters = DeliveryPointSearchRequest(region_id=1, only_in_sectors=False)

    result = await search_delivery_points(filters=filters, db=mock_db_session)

    assert result["total"] == 0
    assert result["items"] == []
    assert mock_db_session.execute.called


@pytest.mark.asyncio
async def test_search_delivery_points_all_in_region(
    mock_db_session, fake_delivery_points_rows
):
    """Test search all delivery points in region."""
    mock_result = MagicMock()
    mock_result.all.return_value = fake_delivery_points_rows
    mock_db_session.execute.return_value = mock_result

    filters = DeliveryPointSearchRequest(region_id=1, only_in_sectors=False)

    result = await search_delivery_points(filters=filters, db=mock_db_session)

    assert result["total"] == 2
    assert len(result["items"]) == 2
    assert mock_db_session.execute.called
    assert result["items"][0]["id"] == 1
    assert result["items"][0]["name"] == "Магазин Пятёрочка"
    assert result["items"][0]["type"] == "Магазин"
    assert result["items"][0]["address"] == "село Казачий Брод, Краснофлотская улица, 27"
    assert result["items"][0]["location"]["type"] == "Point"
    assert "coordinates" in result["items"][0]["location"]
    assert len(result["items"][0]["location"]["coordinates"]) == 2
    assert result["items"][0]["location"]["coordinates"][0] == 39.723098  # longitude
    assert result["items"][0]["location"]["coordinates"][1] == 43.585472  # latitude


@pytest.mark.asyncio
async def test_search_delivery_points_only_in_sectors(
    mock_db_session, fake_delivery_points_rows
):
    """Test search only delivery points inside sectors."""
    mock_result = MagicMock()
    mock_result.all.return_value = [fake_delivery_points_rows[0]]
    mock_db_session.execute.return_value = mock_result
    filters = DeliveryPointSearchRequest(region_id=1, only_in_sectors=True)
    result = await search_delivery_points(filters=filters, db=mock_db_session)

    assert result["total"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0]["id"] == 1
    assert mock_db_session.execute.called


@pytest.mark.asyncio
async def test_search_delivery_points_with_bbox(
    mock_db_session, fake_delivery_points_rows
):
    """Test search delivery points within bounding box."""
    mock_result = MagicMock()
    mock_result.all.return_value = fake_delivery_points_rows
    mock_db_session.execute.return_value = mock_result
    bbox = BoundingBox(min_lng=39.7, min_lat=43.5, max_lng=39.8, max_lat=43.6)
    filters = DeliveryPointSearchRequest(
        region_id=1, only_in_sectors=False, bbox=bbox
    )
    result = await search_delivery_points(filters=filters, db=mock_db_session)

    assert result["total"] == 2
    assert len(result["items"]) == 2
    assert mock_db_session.execute.called


@pytest.mark.asyncio
async def test_search_delivery_points_geojson_format(
    mock_db_session, fake_delivery_points_rows
):
    """Test that location is properly converted to GeoJSON format."""
    mock_result = MagicMock()
    mock_result.all.return_value = [fake_delivery_points_rows[0]]
    mock_db_session.execute.return_value = mock_result
    filters = DeliveryPointSearchRequest(region_id=1, only_in_sectors=False)
    result = await search_delivery_points(filters=filters, db=mock_db_session)

    location = result["items"][0]["location"]
    assert location["type"] == "Point"
    assert isinstance(location["coordinates"], list)
    assert len(location["coordinates"]) == 2
    assert location["coordinates"][0] == 39.723098
    assert location["coordinates"][1] == 43.585472


@pytest.mark.asyncio
async def test_search_delivery_points_response_fields(
    mock_db_session, fake_delivery_points_rows
):
    """Test that response contains all required fields."""
    mock_result = MagicMock()
    mock_result.all.return_value = [fake_delivery_points_rows[0]]
    mock_db_session.execute.return_value = mock_result
    filters = DeliveryPointSearchRequest(region_id=1, only_in_sectors=False)
    result = await search_delivery_points(filters=filters, db=mock_db_session)

    assert "total" in result
    assert "items" in result
    assert result["total"] == 1
    point = result["items"][0]
    assert "id" in point
    assert "name" in point
    assert "type" in point
    assert "title" in point
    assert "address" in point
    assert "address_comment" in point
    assert "landmark" in point
    assert "location" in point
    assert "phone" in point
    assert "mobile" in point
    assert "email" in point
    assert "schedule" in point
    assert "is_active" in point
    assert point["phone"] == "+7 (862) 123-45-67"
    assert point["mobile"] == "+7 (999) 123-45-67"
    assert point["email"] == "shop@example.com"
    assert point["schedule"] == "Пн-Вс: 08:00-22:00"
    assert point["is_active"] is True


@pytest.mark.asyncio
async def test_search_delivery_points_ordered_by_name(
    mock_db_session, fake_delivery_points_rows
):
    """Test that delivery points are ordered by name."""
    reversed_rows = [fake_delivery_points_rows[1], fake_delivery_points_rows[0]]

    mock_result = MagicMock()
    mock_result.all.return_value = reversed_rows
    mock_db_session.execute.return_value = mock_result
    filters = DeliveryPointSearchRequest(region_id=1, only_in_sectors=False)
    result = await search_delivery_points(filters=filters, db=mock_db_session)

    assert result["items"][0]["name"] == "Аптека 36.6"
    assert result["items"][1]["name"] == "Магазин Пятёрочка"


@pytest.mark.asyncio
async def test_search_delivery_points_with_tags(
    mock_db_session, fake_delivery_points_rows
):
    """Test search delivery points filtered by tags."""
    mock_result = MagicMock()
    mock_result.all.return_value = [fake_delivery_points_rows[0]]
    mock_db_session.execute.return_value = mock_result
    filters = DeliveryPointSearchRequest(
        region_id=1, only_in_sectors=False, tag_ids=[1, 2]
    )
    result = await search_delivery_points(filters=filters, db=mock_db_session)

    assert result["total"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0]["id"] == 1
    assert mock_db_session.execute.called


@pytest.mark.asyncio
async def test_search_delivery_points_by_name_prefix(
    mock_db_session, fake_delivery_points_rows
):
    """Test search delivery points by name prefix (3-4 characters)."""
    mock_result = MagicMock()
    mock_result.all.return_value = [fake_delivery_points_rows[0]]
    mock_db_session.execute.return_value = mock_result
    filters = DeliveryPointSearchRequest(
        region_id=1, only_in_sectors=False, search="маг"
    )
    result = await search_delivery_points(filters=filters, db=mock_db_session)

    assert result["total"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0]["name"] == "Магазин Пятёрочка"
    assert mock_db_session.execute.called


@pytest.mark.asyncio
async def test_search_delivery_points_by_name_fuzzy(
    mock_db_session, fake_delivery_points_rows
):
    """Test search delivery points by name with fuzzy search (5+ characters)."""
    mock_result = MagicMock()
    mock_result.all.return_value = [fake_delivery_points_rows[0]]
    mock_db_session.execute.return_value = mock_result
    filters = DeliveryPointSearchRequest(
        region_id=1, only_in_sectors=False, search="магаз"
    )
    result = await search_delivery_points(filters=filters, db=mock_db_session)

    assert result["total"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0]["name"] == "Магазин Пятёрочка"
    assert mock_db_session.execute.called


@pytest.mark.asyncio
async def test_search_delivery_points_with_custom_limit(
    mock_db_session, fake_delivery_points_rows
):
    """Test search delivery points with custom limit."""
    mock_result = MagicMock()
    mock_result.all.return_value = [fake_delivery_points_rows[0]]
    mock_db_session.execute.return_value = mock_result
    filters = DeliveryPointSearchRequest(
        region_id=1, only_in_sectors=False, limit=5
    )
    result = await search_delivery_points(filters=filters, db=mock_db_session)

    assert result["total"] == 1
    assert len(result["items"]) == 1
    assert mock_db_session.execute.called


@pytest.mark.asyncio
async def test_search_delivery_points_search_and_tags(
    mock_db_session, fake_delivery_points_rows
):
    """Test search delivery points with both search and tags filters."""
    mock_result = MagicMock()
    mock_result.all.return_value = [fake_delivery_points_rows[0]]
    mock_db_session.execute.return_value = mock_result
    filters = DeliveryPointSearchRequest(
        region_id=1, only_in_sectors=False, search="маг", tag_ids=[1, 2]
    )
    result = await search_delivery_points(filters=filters, db=mock_db_session)

    assert result["total"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0]["name"] == "Магазин Пятёрочка"
    assert mock_db_session.execute.called
