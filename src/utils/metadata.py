"""Custom metadata injection for the Data Lakehouse platform.

Provides helpers to create standardised ingestion metadata dicts, inject
metadata columns into DataFrames, and persist/load JSON manifest files
in MinIO for downstream lineage tracking.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

import pandas as pd

from src.utils.minio_client import download_to_bytes, upload_bytes

if TYPE_CHECKING:
    from minio import Minio

logger = logging.getLogger(__name__)


def create_ingestion_metadata(
    source_name: str,
    source_url: str,
    api_version: str,
    operator_id: str,
    record_count: int,
    data_format: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a standardised metadata dictionary for an ingestion run.

    An ``ingestion_timestamp`` field is automatically added using the
    current UTC time in ISO-8601 format.

    Parameters
    ----------
    source_name:
        Human-readable name of the data source (e.g. ``"BMKG"``).
    source_url:
        URL or endpoint the data was fetched from.
    api_version:
        Version string of the source API.
    operator_id:
        Identifier for the operator or service account running the
        ingestion.
    record_count:
        Number of records in the ingested payload.
    data_format:
        Format of the raw data (e.g. ``"csv"``, ``"json"``).
    extra:
        Optional dict of additional key-value pairs to merge into the
        metadata.

    Returns
    -------
    dict[str, Any]
        The assembled metadata dictionary.
    """
    metadata: dict[str, Any] = {
        "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
        "source_name": source_name,
        "source_url": source_url,
        "api_version": api_version,
        "operator_id": operator_id,
        "record_count": record_count,
        "data_format": data_format,
    }

    if extra:
        metadata.update(extra)

    logger.debug("Created ingestion metadata: %s", metadata)
    return metadata


def inject_metadata_columns(
    df: pd.DataFrame,
    metadata: dict[str, Any],
) -> pd.DataFrame:
    """Add metadata columns to *df* for lineage tracking.

    The following columns are injected (if the corresponding keys exist
    in *metadata*):

    - ``ingestion_timestamp``
    - ``source_name``
    - ``operator_id``

    Parameters
    ----------
    df:
        The DataFrame to augment.  A copy is returned; the original is
        not modified.
    metadata:
        Metadata dict as produced by :func:`create_ingestion_metadata`.

    Returns
    -------
    pd.DataFrame
        A new DataFrame with the metadata columns appended.
    """
    df = df.copy()

    columns_to_inject = ["ingestion_timestamp", "source_name", "operator_id"]
    for col in columns_to_inject:
        if col in metadata:
            df[col] = metadata[col]
            logger.debug("Injected column '%s' = '%s'", col, metadata[col])
        else:
            logger.warning(
                "Metadata key '%s' not found — column not injected.", col
            )

    return df


def save_manifest(
    client: "Minio",
    bucket_name: str,
    manifest_path: str,
    metadata: dict[str, Any],
) -> None:
    """Persist *metadata* as a JSON manifest file in MinIO.

    Parameters
    ----------
    client:
        An authenticated ``minio.Minio`` instance.
    bucket_name:
        Target bucket.
    manifest_path:
        Object key for the manifest file (e.g.
        ``"bronze/earthquakes/_manifest.json"``).
    metadata:
        The metadata dictionary to serialize.
    """
    payload = json.dumps(metadata, indent=2, ensure_ascii=False, default=str)

    upload_bytes(
        client,
        bucket_name,
        manifest_path,
        payload.encode("utf-8"),
        content_type="application/json",
    )
    logger.info(
        "Saved manifest -> s3://%s/%s",
        bucket_name,
        manifest_path,
    )


def load_manifest(
    client: "Minio",
    bucket_name: str,
    manifest_path: str,
) -> dict[str, Any]:
    """Load a JSON manifest file from MinIO.

    Parameters
    ----------
    client:
        An authenticated ``minio.Minio`` instance.
    bucket_name:
        Source bucket.
    manifest_path:
        Object key of the manifest file.

    Returns
    -------
    dict[str, Any]
        The parsed metadata dictionary.

    Raises
    ------
    FileNotFoundError
        If the manifest object does not exist in MinIO.
    json.JSONDecodeError
        If the manifest contents are not valid JSON.
    """
    try:
        raw = download_to_bytes(client, bucket_name, manifest_path)
    except Exception as exc:
        logger.error(
            "Failed to load manifest from s3://%s/%s",
            bucket_name,
            manifest_path,
        )
        raise FileNotFoundError(
            f"Manifest not found: s3://{bucket_name}/{manifest_path}"
        ) from exc

    metadata = json.loads(raw.decode("utf-8"))
    logger.info(
        "Loaded manifest <- s3://%s/%s",
        bucket_name,
        manifest_path,
    )
    return metadata
