"""Unit tests for countries endpoints."""
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.countries import get_countries, get_country
from app.db.models import Country


@pytest.mark.asyncio
async def test_get_countries_empty(mock_db_session):
    """Test getting countries when database is empty."""
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = []
    mock_db_session.execute.return_value = mock_result

    result = await get_countries(db=mock_db_session)

    assert result == []
    assert mock_db_session.execute.called


@pytest.mark.asyncio
async def test_get_countries_returns_list(mock_db_session, fake_countries):
    """Test getting all countries returns sorted list."""
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = fake_countries
    mock_db_session.execute.return_value = mock_result

    result = await get_countries(db=mock_db_session)

    assert len(result) == 2
    assert result[0].name == "Беларусь"
    assert result[0].code == "BY"
    assert result[1].name == "Россия"
    assert result[1].code == "RU"
    assert mock_db_session.execute.called


@pytest.mark.asyncio
async def test_get_country_by_id_success(mock_db_session, fake_country):
    """Test getting country by ID returns correct country."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fake_country
    mock_db_session.execute.return_value = mock_result

    result = await get_country(country_id=1, db=mock_db_session)

    assert result.id == 1
    assert result.name == "Россия"
    assert result.code == "RU"
    assert mock_db_session.execute.called


@pytest.mark.asyncio
async def test_get_country_by_id_not_found(mock_db_session):
    """Test getting non-existent country raises HTTPException."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await get_country(country_id=999, db=mock_db_session)

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()
    assert "999" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_countries_calls_database(mock_db_session):
    """Test that get_countries calls database execute method."""
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = []
    mock_db_session.execute.return_value = mock_result

    await get_countries(db=mock_db_session)

    assert mock_db_session.execute.called
    assert mock_db_session.execute.call_count == 1


@pytest.mark.asyncio
async def test_get_country_calls_database(mock_db_session):
    """Test that get_country calls database execute method."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = Country(id=1, name="Test", code="TS")
    mock_db_session.execute.return_value = mock_result

    await get_country(country_id=1, db=mock_db_session)

    assert mock_db_session.execute.called
    assert mock_db_session.execute.call_count == 1
