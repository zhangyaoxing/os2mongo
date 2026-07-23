from __future__ import annotations

import logging
import time
from typing import Any

import requests
from pymongo import MongoClient

logger = logging.getLogger(__name__)

_EMBEDDING_API_URL = "https://ai.mongodb.com/v1/embeddings"
_EMBEDDING_MODEL = "voyage-4-large"


class Embedder:
    """Compute embeddings for documents in a MongoDB collection."""

    def __init__(self, mongo_uri: str, database: str, api_key: str) -> None:
        self._client: MongoClient = MongoClient(mongo_uri)
        self._db = self._client[database]
        self._api_key = api_key

    def _compute(self, text: str) -> list[float]:
        resp = requests.post(
            _EMBEDDING_API_URL,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "input": text,
                "model": _EMBEDDING_MODEL,
                "input_type": "document",
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]

    def embed_collection(self, collection: str, batch_size: int = 50) -> dict[str, Any]:
        """Compute embeddings for all documents in *collection* that have
        ``content`` but no ``embedding`` field.

        Returns a summary with ``processed``, ``skipped``, and ``errors``.
        """
        coll = self._db[collection]
        cursor = coll.find(
            {
                "content": {"$exists": True, "$ne": ""},
                "embedding": {"$exists": False},
            },
            {"content": 1},
        )

        processed = 0
        skipped = 0
        errors = 0
        start_time = time.monotonic()

        for doc in cursor:
            content = doc.get("content", "")
            if not content.strip():
                skipped += 1
                continue

            try:
                embedding = self._compute(content)
                coll.update_one(
                    {"_id": doc["_id"]},
                    {
                        "$set": {
                            "embedding": embedding,
                            "embedding_source": _EMBEDDING_MODEL,
                            "embedding_model_id": _EMBEDDING_MODEL,
                        }
                    },
                )
                processed += 1
            except Exception:
                logger.exception("Failed to embed doc %s", doc["_id"])
                errors += 1

            if processed % 10 == 0:
                elapsed = time.monotonic() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                logger.info(
                    "Processed %d docs (%.1f docs/s, %d errors)",
                    processed, rate, errors,
                )

        elapsed = time.monotonic() - start_time
        rate = processed / elapsed if elapsed > 0 else 0
        logger.info(
            "Embedding finished: %d docs in %.1fs (%.1f docs/s, %d skipped, %d errors)",
            processed, elapsed, rate, skipped, errors,
        )

        return {
            "processed": processed,
            "skipped": skipped,
            "errors": errors,
        }
