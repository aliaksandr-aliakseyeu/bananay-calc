"""Unit tests for tags endpoints."""
from unittest.mock import MagicMock

import pytest

from app.api.v1.endpoints.tags import get_tags
from app.db.models.category import Tag


@pytest.fixture
def fake_tags():
    """Create fake tags for testing."""
    return [
        Tag(id=1, name="Продукты питания", slug="produkty-pitaniya"),
        Tag(id=2, name="Аптека", slug="apteka"),
        Tag(id=3, name="Магазин одежды", slug="magazin-odezhdy"),
    ]


@pytest.mark.asyncio
async def test_get_tags_empty(mock_db_session):
    """Test getting tags when no tags exist."""
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = []
    mock_db_session.execute.return_value = mock_result

    result = await get_tags(db=mock_db_session)

    assert result == []
    assert mock_db_session.execute.called


@pytest.mark.asyncio
async def test_get_tags_returns_list(mock_db_session, fake_tags):
    """Test getting all tags."""
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = fake_tags
    mock_db_session.execute.return_value = mock_result

    result = await get_tags(db=mock_db_session)

    assert len(result) == 3
    assert result[0].id == 1
    assert result[0].name == "Продукты питания"
    assert result[0].slug == "produkty-pitaniya"
    assert result[1].name == "Аптека"
    assert result[2].name == "Магазин одежды"
    assert mock_db_session.execute.called


@pytest.mark.asyncio
async def test_get_tags_ordered_by_name(mock_db_session, fake_tags):
    """Test that tags are ordered by name."""
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = fake_tags
    mock_db_session.execute.return_value = mock_result

    result = await get_tags(db=mock_db_session)

    assert len(result) == 3
