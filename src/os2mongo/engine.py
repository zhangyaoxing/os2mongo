from __future__ import annotations

import importlib.util
from typing import Any

from .config import Settings
from .mongodb import MongoWriter
from .opensearch import OpenSearchClient


class MigrationEngine:
    """Orchestrates the migration of documents from OpenSearch to MongoDB."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._os = OpenSearchClient(settings)
        self._mongo = MongoWriter(settings)
        self._transform: Any = None  # Callable[[dict[str, Any]], dict[str, Any]]

        if settings.transform_script:
            self._transform = self._load_transform(settings.transform_script)

    @staticmethod
    def _load_transform(path: str):  # -> Callable[[dict[str, Any]], dict[str, Any]]
        spec = importlib.util.spec_from_file_location("transform", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load transform script: {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not hasattr(module, "transform"):
            raise AttributeError(f"Transform script must define a 'transform' function: {path}")
        return module.transform

    def check_connections(self) -> dict[str, bool]:
        return {
            "opensearch": self._os.ping(),
            "mongodb": self._mongo.ping(),
        }

    def _build_date_query(self) -> dict[str, Any] | None:
        """Parse date_field and date_range into an OpenSearch range query.

        date_range format: ``"gte,lte"`` — either side can be empty.
        Example: ``"2024-01-01,2024-12-31"``, ``"2024-01-01,"``, ``",2024-12-31"``.
        """
        if not self._settings.date_field or not self._settings.date_range:
            return None

        parts = self._settings.date_range.split(",", 1)
        if len(parts) != 2:
            return None

        gte, lte = parts[0].strip(), parts[1].strip()
        range_body: dict[str, Any] = {}
        if gte:
            range_body["gte"] = gte
        if lte:
            range_body["lte"] = lte

        if not range_body:
            return None

        return {"range": {self._settings.date_field: range_body}}

    @staticmethod
    def _merge_queries(
        base: dict[str, Any] | None, extra: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Merge two OpenSearch query dicts with a bool must clause."""
        if not base and not extra:
            return None
        if not base:
            return extra
        if not extra:
            return base
        return {"bool": {"must": [base, extra]}}

    def migrate(
        self,
        source_index: str,
        target_collection: str | None = None,
        query: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run the full migration from an OpenSearch index to a MongoDB collection.

        Returns a summary dict with ``total``, ``inserted``, and ``errors``.
        """
        target = target_collection or source_index

        if self._settings.drop_existing:
            self._mongo.drop_collection(target)

        merged_query = self._merge_queries(query, self._build_date_query())

        total = self._os.get_index_count(source_index, query=merged_query)
        if total == 0:
            return {"total": 0, "inserted": 0, "errors": 0}

        inserted = 0
        errors = 0
        batch: list[dict[str, Any]] = []
        collection = self._mongo.get_collection(target)

        for doc in self._os.scan_documents(source_index, query=merged_query):
            if self._transform:
                try:
                    doc = self._transform(doc)
                except Exception:
                    errors += 1
                    continue

            batch.append(doc)

            if len(batch) >= self._settings.batch_size:
                inserted += self._mongo.bulk_insert(collection, batch)
                batch = []

        if batch:
            inserted += self._mongo.bulk_insert(collection, batch)

        return {"total": total, "inserted": inserted, "errors": errors}
