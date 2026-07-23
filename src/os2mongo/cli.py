from __future__ import annotations

import json
import logging
import sys

import click
from dotenv import load_dotenv

from .config import Settings
from .engine import MigrationEngine

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)


@click.group()
@click.version_option()
def main() -> None:
    """os2mongo - OpenSearch to MongoDB migration tool."""


@main.command()
@click.argument("source_index")
@click.option(
    "-t",
    "--target-collection",
    default=None,
    help="Target MongoDB collection (defaults to source index name).",
)
@click.option(
    "-q",
    "--query",
    default=None,
    help="JSON query to filter documents (OpenSearch query DSL).",
)
@click.option(
    "--drop-existing",
    is_flag=True,
    default=None,
    help="Drop the target collection before migration.",
)
@click.option(
    "--transform",
    default=None,
    type=click.Path(exists=True),
    help="Path to a Python transform script.",
)
@click.option(
    "--transform-dir",
    default=None,
    type=click.Path(exists=True, file_okay=False),
    help="Directory of Python transform scripts (loaded in alphabetical order).",
)
def migrate(
    source_index: str,
    target_collection: str | None,
    query: str | None,
    drop_existing: bool | None,
    transform: str | None,
    transform_dir: str | None,
) -> None:
    """Migrate documents from an OpenSearch index to a MongoDB collection."""
    settings = Settings()
    if drop_existing is not None:
        settings.drop_existing = drop_existing
    if transform:
        settings.transform_script = transform  # type: ignore[assignment]
    if transform_dir:
        settings.transform_dir = transform_dir  # type: ignore[assignment]

    query_dict: dict | None = None
    query_str = query or settings.query
    if query_str:
        try:
            query_dict = json.loads(query_str)
        except json.JSONDecodeError as e:
            click.echo(f"Error: invalid JSON query: {e}", err=True)
            sys.exit(1)

    engine = MigrationEngine(settings)

    click.echo("Checking connections...")
    status = engine.check_connections()
    for service, ok in status.items():
        symbol = "✓" if ok else "✗"
        click.echo(f"  {symbol} {service}")
    if not all(status.values()):
        click.echo("Error: connection check failed.", err=True)
        sys.exit(1)

    click.echo(f"Migrating '{source_index}' -> '{target_collection or source_index}' ...")
    result = engine.migrate(source_index, target_collection, query_dict)
    click.echo(
        f"Done. Total: {result['total']}, "
        f"Inserted: {result['inserted']}, "
        f"Errors: {result['errors']}"
    )


@main.command()
def check() -> None:
    """Check connectivity to OpenSearch and MongoDB."""
    settings = Settings()
    engine = MigrationEngine(settings)
    status = engine.check_connections()
    for service, ok in status.items():
        symbol = "✓" if ok else "✗"
        click.echo(f"  {symbol} {service}")
    if not all(status.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
