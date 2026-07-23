# os2mongo

OpenSearch to MongoDB migration tool.

## Installation

```bash
git clone git@github.com:zhangyaoxing/os2mongo.git
cd os2mongo
pip install -e .
```

## Configuration

All settings are loaded from environment variables with the `OS2MONGO_` prefix, or from a `.env` file in the project root.

| Variable                           | Default                     | Description                                            |
| ---------------------------------- | --------------------------- | ------------------------------------------------------ |
| `OS2MONGO_OPENSEARCH_HOST`         | `localhost`                 | OpenSearch host                                        |
| `OS2MONGO_OPENSEARCH_PORT`         | `9200`                      | OpenSearch port                                        |
| `OS2MONGO_OPENSEARCH_USE_SSL`      | `false`                     | Use HTTPS                                              |
| `OS2MONGO_OPENSEARCH_VERIFY_CERTS` | `true`                      | Verify SSL certificates                                |
| `OS2MONGO_OPENSEARCH_USERNAME`     | —                           | Username for Basic Auth                                |
| `OS2MONGO_OPENSEARCH_PASSWORD`     | —                           | Password for Basic Auth                                |
| `OS2MONGO_MONGODB_URI`             | `mongodb://localhost:27017` | MongoDB connection URI                                 |
| `OS2MONGO_MONGODB_DATABASE`        | `os2mongo`                  | Target database name                                   |
| `OS2MONGO_BATCH_SIZE`              | `1000`                      | Documents per bulk insert batch                        |
| `OS2MONGO_SCROLL_TIME`             | `5m`                        | OpenSearch scroll keep-alive                           |
| `OS2MONGO_REPORT_INTERVAL`         | `10`                        | Progress logging interval in seconds                   |
| `OS2MONGO_DROP_EXISTING`           | `false`                     | Drop target collection before migration                |
| `OS2MONGO_QUERY`                   | —                           | Default query in OpenSearch DSL (overridden by `-q`)   |
| `OS2MONGO_TRANSFORM_SCRIPT`        | —                           | Path to a single Python transform script               |
| `OS2MONGO_TRANSFORM_DIR`           | `transformers`              | Directory of transform scripts (loaded alphabetically) |
| `OS2MONGO_EMBEDDING_API_KEY`       | —                           | API key for MongoDB AI Embedding API                  |
| `OS2MONGO_EMBED_WORKERS`           | `4`                         | Number of concurrent embedding workers                |

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
| `--transform-dir`         | Directory of Python transform scripts (loaded alphabetically)  |

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

Use a directory of transform scripts (loaded in alphabetical order):

```bash
os2mongo migrate my-index --transform-dir transformers
```

The default value of `--transform-dir` is `transformers`, so scripts in that directory are
loaded automatically — no CLI flag or `.env` setting needed.

Filter by date range:

```bash
os2mongo migrate my-index -q '{"range": {"upload_date.keyword": {"gte": "07-04-2026", "lte": "07-05-2026"}}}'
```

Combine filters with `bool`:

```bash
os2mongo migrate my-index -q '{"bool": {"must": [{"range": {"upload_date.keyword": {"gte": "07-04-2026"}}}, {"match": {"status": "active"}}]}}'
```

Set a default query in `.env` (no CLI `-q` needed):

```env
OS2MONGO_QUERY={"range": {"upload_date.keyword": {"gte": "07-04-2026", "lte": "07-05-2026"}}}
```
