from __future__ import annotations

from typing import Any

from pymongo import MongoClient as PyMongoClient
from pymongo.collection import Collection

from .config import Settings


class MongoWriter:
    """Wraps the MongoDB client for bulk document import."""

    def __init__(self, settings: Settings) -> None:
        self._client: PyMongoClient = PyMongoClient(settings.mongodb_uri)
        self._settings = settings

    def ping(self) -> bool:
        try:
            self._client.admin.command("ping")
            return True
        except Exception:
            return False

    def get_collection(self, name: str) -> Collection:
        db = self._client[self._settings.mongodb_database]
        return db[name]

    def drop_collection(self, name: str) -> None:
        db = self._client[self._settings.mongodb_database]
        db.drop_collection(name)

    def bulk_insert(self, collection: Collection, documents: list[dict[str, Any]]) -> int:
        """Insert documents in bulk. Returns count of inserted documents."""
        if not documents:
            return 0
        result = collection.insert_many(documents, ordered=False)
        return len(result.inserted_ids)

    def count_documents(self, collection: str) -> int:
        return self.get_collection(collection).count_documents({})
