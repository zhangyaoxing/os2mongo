from __future__ import annotations

from unittest.mock import MagicMock, patch

from os2mongo.config import Settings
from os2mongo.engine import MigrationEngine


class TestMigrationEngine:
    def test_check_connections_both_ok(self, settings: Settings) -> None:
        with (
            patch("os2mongo.engine.OpenSearchClient.ping", return_value=True),
            patch("os2mongo.engine.MongoWriter.ping", return_value=True),
        ):
            engine = MigrationEngine(settings)
            result = engine.check_connections()
            assert result == {"opensearch": True, "mongodb": True}

    def test_check_connections_mongo_down(self, settings: Settings) -> None:
        with (
            patch("os2mongo.engine.OpenSearchClient.ping", return_value=True),
            patch("os2mongo.engine.MongoWriter.ping", return_value=False),
        ):
            engine = MigrationEngine(settings)
            result = engine.check_connections()
            assert result == {"opensearch": True, "mongodb": False}

    def test_migrate_empty_index(self, settings: Settings) -> None:
        with (
            patch("os2mongo.engine.OpenSearchClient.get_index_count", return_value=0),
            patch("os2mongo.engine.MongoWriter.drop_collection"),
        ):
            engine = MigrationEngine(settings)
            result = engine.migrate("test_index")
            assert result == {"total": 0, "inserted": 0, "errors": 0}

    def test_migrate_with_documents(self, settings: Settings) -> None:
        docs = [{"_id": i, "name": f"doc{i}"} for i in range(5)]

        with (
            patch("os2mongo.engine.OpenSearchClient.get_index_count", return_value=5),
            patch(
                "os2mongo.engine.OpenSearchClient.scan_documents",
                return_value=iter(docs),
            ),
            patch("os2mongo.engine.MongoWriter.bulk_insert", return_value=5),
            patch("os2mongo.engine.MongoWriter.get_collection", return_value=MagicMock()),
        ):
            engine = MigrationEngine(settings)
            result = engine.migrate("test_index")
            assert result == {"total": 5, "inserted": 5, "errors": 0}

    def test_migrate_with_drop_existing(self, settings: Settings) -> None:
        settings.drop_existing = True
        docs = [{"_id": 1}]

        with (
            patch("os2mongo.engine.OpenSearchClient.get_index_count", return_value=1),
            patch(
                "os2mongo.engine.OpenSearchClient.scan_documents",
                return_value=iter(docs),
            ),
            patch("os2mongo.engine.MongoWriter.drop_collection") as mock_drop,
            patch("os2mongo.engine.MongoWriter.bulk_insert", return_value=1),
            patch("os2mongo.engine.MongoWriter.get_collection", return_value=MagicMock()),
        ):
            engine = MigrationEngine(settings)
            engine.migrate("test_index")
            mock_drop.assert_called_once_with("test_index")

    def test_migrate_with_transform(self, settings: Settings, tmp_path: str) -> None:
        import os

        transform_path = os.path.join(tmp_path, "transform.py")
        with open(transform_path, "w") as f:
            f.write("def transform(doc):\n    doc['transformed'] = True\n    return doc\n")

        settings.transform_script = transform_path
        docs = [{"_id": 1, "name": "test"}]

        def fake_bulk_insert(collection, docs_list):
            assert docs_list[0]["transformed"] is True
            return 1

        with (
            patch("os2mongo.engine.OpenSearchClient.get_index_count", return_value=1),
            patch(
                "os2mongo.engine.OpenSearchClient.scan_documents",
                return_value=iter(docs),
            ),
            patch("os2mongo.engine.MongoWriter.bulk_insert", side_effect=fake_bulk_insert),
            patch("os2mongo.engine.MongoWriter.get_collection", return_value=MagicMock()),
        ):
            engine = MigrationEngine(settings)
            result = engine.migrate("test_index")
            assert result["inserted"] == 1

    def test_build_date_query_full_range(self, settings: Settings) -> None:
        settings.date_field = "upload_date"
        settings.date_range = "2024-01-01,2024-12-31"
        engine = MigrationEngine(settings)
        result = engine._build_date_query()
        assert result == {"range": {"upload_date": {"gte": "2024-01-01", "lte": "2024-12-31"}}}

    def test_build_date_query_gte_only(self, settings: Settings) -> None:
        settings.date_field = "upload_date"
        settings.date_range = "2024-01-01,"
        engine = MigrationEngine(settings)
        result = engine._build_date_query()
        assert result == {"range": {"upload_date": {"gte": "2024-01-01"}}}

    def test_build_date_query_lte_only(self, settings: Settings) -> None:
        settings.date_field = "upload_date"
        settings.date_range = ",2024-12-31"
        engine = MigrationEngine(settings)
        result = engine._build_date_query()
        assert result == {"range": {"upload_date": {"lte": "2024-12-31"}}}

    def test_build_date_query_no_field(self, settings: Settings) -> None:
        settings.date_range = "2024-01-01,2024-12-31"
        engine = MigrationEngine(settings)
        assert engine._build_date_query() is None

    def test_build_date_query_no_range(self, settings: Settings) -> None:
        settings.date_field = "upload_date"
        engine = MigrationEngine(settings)
        assert engine._build_date_query() is None

    def test_merge_queries_both(self, settings: Settings) -> None:
        engine = MigrationEngine(settings)
        base = {"match": {"status": "active"}}
        extra = {"range": {"upload_date": {"gte": "2024-01-01"}}}
        result = engine._merge_queries(base, extra)
        assert result == {"bool": {"must": [base, extra]}}

    def test_merge_queries_base_only(self, settings: Settings) -> None:
        engine = MigrationEngine(settings)
        base = {"match": {"status": "active"}}
        assert engine._merge_queries(base, None) == base

    def test_merge_queries_extra_only(self, settings: Settings) -> None:
        engine = MigrationEngine(settings)
        extra = {"range": {"upload_date": {"gte": "2024-01-01"}}}
        assert engine._merge_queries(None, extra) == extra

    def test_merge_queries_both_none(self, settings: Settings) -> None:
        engine = MigrationEngine(settings)
        assert engine._merge_queries(None, None) is None

    def test_migrate_passes_date_query(self, settings: Settings) -> None:
        settings.date_field = "upload_date"
        settings.date_range = "2024-01-01,2024-12-31"
        docs = [{"_id": 1}]

        with (
            patch("os2mongo.engine.OpenSearchClient.get_index_count", return_value=1),
            patch(
                "os2mongo.engine.OpenSearchClient.scan_documents",
                return_value=iter(docs),
            ) as mock_scan,
            patch("os2mongo.engine.MongoWriter.bulk_insert", return_value=1),
            patch("os2mongo.engine.MongoWriter.get_collection", return_value=MagicMock()),
        ):
            engine = MigrationEngine(settings)
            engine.migrate("test_index")
            expected = {"range": {"upload_date": {"gte": "2024-01-01", "lte": "2024-12-31"}}}
            mock_scan.assert_called_once_with("test_index", query=expected)
