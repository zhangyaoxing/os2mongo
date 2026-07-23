from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for os2mongo, loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_prefix="OS2MONGO_", env_file=".env", env_file_encoding="utf-8"
    )

    # OpenSearch
    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_use_ssl: bool = False
    opensearch_verify_certs: bool = True
    opensearch_username: str | None = None
    opensearch_password: str | None = None

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "os2mongo"

    # Migration
    batch_size: int = 1000
    scroll_time: str = "5m"
    transform_script: Path | None = None
    transform_dir: Path | None = Path("transformers")
    drop_existing: bool = False
    query: str | None = None

    @property
    def opensearch_url(self) -> str:
        scheme = "https" if self.opensearch_use_ssl else "http"
        return f"{scheme}://{self.opensearch_host}:{self.opensearch_port}"
