from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from opensearchpy import OpenSearch
from opensearchpy.helpers import scan

from .config import Settings


class OpenSearchClient:
    """Wraps the OpenSearch client for scroll-based document export."""

    def __init__(self, settings: Settings) -> None:
        http_auth = None
        if settings.opensearch_username and settings.opensearch_password:
            http_auth = (settings.opensearch_username, settings.opensearch_password)

        self._client = OpenSearch(
            hosts=[settings.opensearch_url],
            http_auth=http_auth,
            use_ssl=settings.opensearch_use_ssl,
            verify_certs=settings.opensearch_verify_certs,
        )
        self._settings = settings

    def ping(self) -> bool:
        try:
            return self._client.ping()
        except Exception:
            return False

    def get_index_count(
        self, index: str, query: dict[str, Any] | None = None
    ) -> int:
        body: dict[str, Any] = {}
        if query:
            body["query"] = query
        return self._client.count(index=index, body=body)["count"]

    def scan_documents(
        self, index: str, query: dict[str, Any] | None = None
    ) -> Iterator[dict[str, Any]]:
        """Yield all documents from an index using scroll."""
        body: dict[str, Any] = {}
        if query:
            body["query"] = query

        for hit in scan(
            self._client,
            index=index,
            query=body,
            scroll=self._settings.scroll_time,
            size=self._settings.batch_size,
        ):
            yield hit["_source"]
