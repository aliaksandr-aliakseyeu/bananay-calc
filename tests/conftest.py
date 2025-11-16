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
        Country(id=1, name="Беларусь", code="BY"),
        Country(id=2, name="Россия", code="RU"),
    ]


@pytest.fixture
def fake_country():
    """
    Create single fake country for testing.

    Returns single Country object with test data.
    """
    return Country(id=1, name="Россия", code="RU")
