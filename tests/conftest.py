"""Pytest configuration and fixtures for unit tests."""
from unittest.mock import AsyncMock

import pytest

from app.db.models import Country


@pytest.fixture
def mock_db_session():
    """
    Create mock database session.

    Returns AsyncMock that can be used instead of real database session.
    """
    return AsyncMock()


@pytest.fixture
def fake_countries():
    """
    Create fake countries data for testing.

    Returns list of Country objects with test data.
    """
    return [
        Country(id=1, name="Belarus", code="BY", name_i18n={"ru": "Беларусь", "en": "Belarus", "ka": "ბელარუსი"}),
        Country(id=2, name="Russia", code="RU", name_i18n={"ru": "Россия", "en": "Russia", "ka": "რუსეთი"}),
    ]


@pytest.fixture
def fake_country():
    """
    Create single fake country for testing.

    Returns single Country object with test data.
    """
    return Country(
        id=1,
        name="Russia",
        code="RU",
        name_i18n={"ru": "Россия", "en": "Russia", "ka": "რუსეთი"},
    )
