"""
Settings module for the Data Lakehouse project.

This module centralizes all configuration by loading environment variables
from a .env file and exposing them as module-level constants. It also
provides factory functions for creating pre-configured MinIO and DuckDB
clients used throughout the project.

Usage:
    from config.settings import MINIO_ENDPOINT, get_minio_client
    client = get_minio_client()
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from minio import Minio

# ---------------------------------------------------------------------------
# Load environment variables from the .env file located at the project root.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DOTENV_PATH = _PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=_DOTENV_PATH)

# ---------------------------------------------------------------------------
# MinIO connection settings
# ---------------------------------------------------------------------------
MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
"""Hostname and port of the MinIO server (e.g. ``localhost:9000``)."""

MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
"""Access key (username) used to authenticate with MinIO."""

MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
"""Secret key (password) used to authenticate with MinIO."""

MINIO_BUCKET_NAME: str = os.getenv("MINIO_BUCKET_NAME", "datalakehouse")
"""Default bucket name where all lakehouse data is stored."""

MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() in ("true", "1", "yes")
"""Whether to use TLS/SSL when connecting to MinIO."""

# ---------------------------------------------------------------------------
# Medallion architecture layer prefixes
# ---------------------------------------------------------------------------
BRONZE_PREFIX: str = "bronze/"
"""Object-key prefix for the Bronze (raw ingestion) layer."""

SILVER_PREFIX: str = "silver/"
"""Object-key prefix for the Silver (cleansed / conformed) layer."""

GOLD_PREFIX: str = "gold/"
"""Object-key prefix for the Gold (business-level aggregates) layer."""

# ---------------------------------------------------------------------------
# Wikidata SPARQL settings
# ---------------------------------------------------------------------------
WIKIDATA_SPARQL_ENDPOINT: str = "https://query.wikidata.org/sparql"
"""URL of the Wikidata SPARQL query service."""

WIKIDATA_USER_AGENT: str = "DataLakehouseProject/1.0 (university-project)"
"""User-Agent header sent with every request to the Wikidata API."""


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------

def get_minio_client() -> Minio:
    """Return a configured :class:`minio.Minio` client instance.

    The client is created using the module-level connection constants
    (``MINIO_ENDPOINT``, ``MINIO_ACCESS_KEY``, ``MINIO_SECRET_KEY``,
    ``MINIO_SECURE``).  A new client is created on every call so that
    callers are free to use it in any threading context.

    Returns:
        Minio: A ready-to-use MinIO client.

    Example::

        from config.settings import get_minio_client, MINIO_BUCKET_NAME
        client = get_minio_client()
        if not client.bucket_exists(MINIO_BUCKET_NAME):
            client.make_bucket(MINIO_BUCKET_NAME)
    """
    return Minio(
        endpoint=MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE,
    )


def get_duckdb_connection():
    """Return a new DuckDB connection with required extensions loaded.

    The connection is configured with the ``httpfs`` extension installed
    and loaded so that DuckDB can read Parquet files directly from MinIO
    (S3-compatible) storage.  The S3 credentials are set to match the
    module-level MinIO constants.

    Returns:
        duckdb.DuckDBPyConnection: A DuckDB connection ready for queries.

    Example::

        from config.settings import get_duckdb_connection
        con = get_duckdb_connection()
        df = con.execute("SELECT * FROM 's3://datalakehouse/gold/table.parquet'").fetchdf()
    """
    import duckdb

    con = duckdb.connect()

    # Install and load the httpfs extension for S3/MinIO access.
    con.install_extension("httpfs")
    con.load_extension("httpfs")

    # Point DuckDB's S3 layer at the local MinIO instance.
    con.execute(f"SET s3_endpoint = '{MINIO_ENDPOINT}';")
    con.execute(f"SET s3_access_key_id = '{MINIO_ACCESS_KEY}';")
    con.execute(f"SET s3_secret_access_key = '{MINIO_SECRET_KEY}';")
    con.execute(f"SET s3_use_ssl = {'true' if MINIO_SECURE else 'false'};")
    con.execute("SET s3_url_style = 'path';")

    return con
