from __future__ import annotations

import logging
import os
import queue
import threading
import time
from typing import Any

import requests
from pymongo import MongoClient

logger = logging.getLogger(__name__)

_EMBEDDING_API_URL = "https://ai.mongodb.com/v1/embeddings"
_EMBEDDING_MODEL = "voyage-4-large"
_SENTINEL = None


def _num_workers() -> int:
    return int(os.environ.get("OS2MONGO_EMBED_WORKERS", "4"))


class Embedder:
    """Compute embeddings for documents in a MongoDB collection using
    a producer-consumer pattern.
    """

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

    def embed_collection(self, collection: str) -> dict[str, Any]:
        """Compute embeddings for all documents in *collection* that have
        ``content`` but no ``embedding`` field.

        Returns a summary with ``processed``, ``skipped``, and ``errors``.
        """
        coll = self._db[collection]
        workers_count = _num_workers()
        task_queue: queue.Queue[tuple[str, str] | None] = queue.Queue(
            maxsize=workers_count * 2
        )
        lock = threading.Lock()
        stats: dict[str, int] = {"processed": 0, "skipped": 0, "errors": 0}
        start_time = time.monotonic()

        def consumer(worker_id: int) -> None:
            local_count = 0
            while True:
                item = task_queue.get()
                if item is _SENTINEL:
                    if local_count:
                        logger.info(
                            "[worker %d] processed %d docs", worker_id, local_count
                        )
                    task_queue.task_done()
                    return

                doc_id, content = item
                try:
                    if not content.strip():
                        with lock:
                            stats["skipped"] += 1
                        task_queue.task_done()
                        continue

                    embedding = self._compute(content)
                    self._db[collection].update_one(
                        {"_id": doc_id},
                        {
                            "$set": {
                                "embedding": embedding,
                                "embedding_source": _EMBEDDING_MODEL,
                                "embedding_model_id": _EMBEDDING_MODEL,
                            }
                        },
                    )
                    with lock:
                        stats["processed"] += 1
                    local_count += 1
                    if local_count % 100 == 0:
                        with lock:
                            elapsed = time.monotonic() - start_time
                            rate = stats["processed"] / elapsed if elapsed > 0 else 0
                        logger.info(
                            "[worker %d] %d docs (total %d, %.1f docs/s)",
                            worker_id,
                            local_count,
                            stats["processed"],
                            rate,
                        )
                except Exception:
                    logger.exception("Failed to embed doc %s", doc_id)
                    with lock:
                        stats["errors"] += 1
                finally:
                    task_queue.task_done()

        # Start consumers
        workers = [
            threading.Thread(target=consumer, args=(i,), daemon=True)
            for i in range(workers_count)
        ]
        for w in workers:
            w.start()

        # Producer: read from MongoDB
        cursor = coll.find(
            {
                "content": {"$exists": True, "$ne": ""},
                "embedding": {"$exists": False},
            },
            {"content": 1},
        )
        for doc in cursor:
            task_queue.put((doc["_id"], doc.get("content", "")))

        # Signal consumers to stop and wait for completion
        for _ in workers:
            task_queue.put(_SENTINEL)
        task_queue.join()
        for w in workers:
            w.join()

        elapsed = time.monotonic() - start_time
        rate = stats["processed"] / elapsed if elapsed > 0 else 0
        logger.info(
            "Embedding finished: %d docs in %.1fs (%.1f docs/s, %d skipped, %d errors)",
            stats["processed"], elapsed, rate, stats["skipped"], stats["errors"],
        )

        return dict(stats)
