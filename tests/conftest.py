from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from os2mongo.config import Settings


@pytest.fixture(autouse=True)
def _mock_pymongo() -> None:
    """Prevent any test from connecting to a real MongoDB instance."""
    with patch("os2mongo.mongodb.PyMongoClient", return_value=MagicMock()):
        yield


@pytest.fixture
def settings() -> Settings:
    return Settings(
        opensearch_host="localhost",
        opensearch_port=9200,
        mongodb_uri="mongodb://localhost:27017",
        mongodb_database="test_os2mongo",
        batch_size=10,
        date_field=None,
        date_range=None,
    )
