"""MD5 / ETag-based checksum utilities for idempotent data ingestion.

This module provides helpers to compute, store, and compare MD5 checksums
so that pipeline stages can skip re-processing when the source data has
not changed.  Checksums are persisted as small text objects in MinIO.
"""

from __future__ import annotations

import hashlib
import io
import logging
from typing import TYPE_CHECKING

import pandas as pd

from src.utils.minio_client import (
    download_to_bytes,
    object_exists,
    upload_bytes,
)

if TYPE_CHECKING:
    from minio import Minio

logger = logging.getLogger(__name__)


def compute_md5(data: bytes) -> str:
    """Compute the hex-encoded MD5 digest of *data*.

    Parameters
    ----------
    data:
        Raw bytes to hash.

    Returns
    -------
    str
        32-character lowercase hex MD5 digest.
    """
    return hashlib.md5(data).hexdigest()


def compute_dataframe_md5(df: pd.DataFrame) -> str:
    """Serialize *df* to CSV bytes (no index) and compute the MD5.

    Deterministic serialization is achieved by always writing with
    ``index=False`` so the same logical data produces the same hash.

    Parameters
    ----------
    df:
        The DataFrame to hash.

    Returns
    -------
    str
        32-character lowercase hex MD5 digest.
    """
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False)
    return compute_md5(buffer.getvalue())


def get_stored_checksum(
    client: "Minio",
    bucket_name: str,
    checksum_path: str,
) -> str | None:
    """Read a previously stored checksum from MinIO.

    Parameters
    ----------
    client:
        An authenticated ``minio.Minio`` instance.
    bucket_name:
        The bucket containing the checksum file.
    checksum_path:
        Object key where the checksum is stored.

    Returns
    -------
    str | None
        The stored checksum string, or ``None`` if it does not exist.
    """
    if not object_exists(client, bucket_name, checksum_path):
        logger.debug("No stored checksum at s3://%s/%s", bucket_name, checksum_path)
        return None

    raw = download_to_bytes(client, bucket_name, checksum_path)
    checksum = raw.decode("utf-8").strip()
    logger.debug(
        "Loaded stored checksum '%s' from s3://%s/%s",
        checksum,
        bucket_name,
        checksum_path,
    )
    return checksum


def store_checksum(
    client: "Minio",
    bucket_name: str,
    checksum_path: str,
    checksum: str,
) -> None:
    """Write *checksum* as a UTF-8 text object to MinIO.

    Parameters
    ----------
    client:
        An authenticated ``minio.Minio`` instance.
    bucket_name:
        The target bucket.
    checksum_path:
        Object key where the checksum will be stored.
    checksum:
        The checksum string to persist.
    """
    upload_bytes(
        client,
        bucket_name,
        checksum_path,
        checksum.encode("utf-8"),
        content_type="text/plain",
    )
    logger.info(
        "Stored checksum '%s' -> s3://%s/%s",
        checksum,
        bucket_name,
        checksum_path,
    )


def has_data_changed(
    client: "Minio",
    bucket_name: str,
    checksum_path: str,
    new_checksum: str,
) -> bool:
    """Compare *new_checksum* against the stored checksum in MinIO.

    Returns ``True`` if the data has changed (i.e. checksums differ) or
    if no previous checksum exists.  Returns ``False`` when the checksums
    match, meaning the data is unchanged and processing can be skipped.

    Parameters
    ----------
    client:
        An authenticated ``minio.Minio`` instance.
    bucket_name:
        The bucket containing the checksum file.
    checksum_path:
        Object key where the previous checksum is stored.
    new_checksum:
        The freshly computed checksum to compare.

    Returns
    -------
    bool
        ``True`` if data changed or no prior checksum; ``False`` otherwise.
    """
    stored = get_stored_checksum(client, bucket_name, checksum_path)

    if stored is None:
        logger.info(
            "No previous checksum found at s3://%s/%s — treating as changed.",
            bucket_name,
            checksum_path,
        )
        return True

    changed = stored != new_checksum
    if changed:
        logger.info(
            "Checksum changed: stored=%s, new=%s (s3://%s/%s)",
            stored,
            new_checksum,
            bucket_name,
            checksum_path,
        )
    else:
        logger.info(
            "Checksum unchanged: %s (s3://%s/%s)",
            stored,
            bucket_name,
            checksum_path,
        )
    return changed
