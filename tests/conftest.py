from __future__ import annotations

import pytest

from os2mongo.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        opensearch_host="localhost",
        opensearch_port=9200,
        mongodb_uri="mongodb://localhost:27017",
        mongodb_database="test_os2mongo",
        batch_size=10,
    )
