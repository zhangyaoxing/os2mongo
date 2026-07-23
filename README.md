# os2mongo

OpenSearch to MongoDB migration tool.

## Installation

```bash
pip install -e .
```

## Configuration

All settings are loaded from environment variables with the `OS2MONGO_` prefix, or from a `.env` file in the project root.

| Variable                           | Default                     | Description                                                |
| ---------------------------------- | --------------------------- | ---------------------------------------------------------- |
| `OS2MONGO_OPENSEARCH_HOST`         | `localhost`                 | OpenSearch host                                            |
| `OS2MONGO_OPENSEARCH_PORT`         | `9200`                      | OpenSearch port                                            |
| `OS2MONGO_OPENSEARCH_USE_SSL`      | `false`                     | Use HTTPS                                                  |
| `OS2MONGO_OPENSEARCH_VERIFY_CERTS` | `true`                      | Verify SSL certificates                                    |
| `OS2MONGO_OPENSEARCH_USERNAME`     | —                           | Username for Basic Auth                                    |
| `OS2MONGO_OPENSEARCH_PASSWORD`     | —                           | Password for Basic Auth                                    |
| `OS2MONGO_MONGODB_URI`             | `mongodb://localhost:27017` | MongoDB connection URI                                     |
| `OS2MONGO_MONGODB_DATABASE`        | `os2mongo`                  | Target database name                                       |
| `OS2MONGO_BATCH_SIZE`              | `1000`                      | Documents per bulk insert batch                            |
| `OS2MONGO_SCROLL_TIME`             | `5m`                        | OpenSearch scroll keep-alive                               |
| `OS2MONGO_DROP_EXISTING`           | `false`                     | Drop target collection before migration                    |
| `OS2MONGO_DATE_FIELD`              | —                           | Field name for date-range filtering                        |
| `OS2MONGO_DATE_RANGE`              | —                           | Date range as `"gte,lte"` (e.g. `"2024-01-01,2024-12-31"`) |

## Usage

### Check connectivity

```bash
os2mongo check
```

### Migrate an index

```bash
os2mongo migrate my-index
```

Migrate all documents from the `my-index` OpenSearch index to a `my-index` MongoDB collection.

### Options

| Option                    | Description                                                    |
| ------------------------- | -------------------------------------------------------------- |
| `-t, --target-collection` | Target MongoDB collection name (defaults to source index name) |
| `-q, --query`             | JSON query in OpenSearch DSL to filter documents               |
| `--drop-existing`         | Drop the target collection before migrating                    |
| `--transform`             | Path to a Python transform script                              |
| `--date-field`            | Field name for date-range filtering                            |
| `--date-range`            | Date range as `"gte,lte"` (e.g. `"2024-01-01,2024-12-31"`)     |

### Examples

Filter documents with a query:

```bash
os2mongo migrate my-index -q '{"match": {"status": "active"}}'
```

Custom target collection with drop:

```bash
os2mongo migrate my-index -t archive --drop-existing
```

Use a transform script (`transform.py`):

```bash
os2mongo migrate my-index --transform ./transform.py
```

The transform script must define a `transform(doc)` function:

```python
def transform(doc):
    doc["_id"] = doc.pop("id")
    doc["migrated_at"] = "2026-07-23"
    return doc
```

Filter by date range using `upload_date` field:

```bash
os2mongo migrate my-index --date-field upload_date --date-range "2024-01-01,2024-12-31"
```
