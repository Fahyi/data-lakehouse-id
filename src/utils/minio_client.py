"""MinIO helper functions for the Data Lakehouse platform.

Provides high-level wrappers around the ``minio`` library for bucket
management, DataFrame upload/download (CSV and Parquet), raw byte
operations, and object introspection.  All in-memory I/O is handled
through ``io.BytesIO`` to avoid temporary files on disk.
"""

from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from minio import Minio

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bucket management
# ---------------------------------------------------------------------------

def ensure_bucket_exists(client: "Minio", bucket_name: str) -> None:
    """Create *bucket_name* if it does not already exist.

    Parameters
    ----------
    client:
        An authenticated ``minio.Minio`` instance.
    bucket_name:
        Name of the bucket to create.

    Raises
    ------
    minio.error.S3Error
        If the MinIO server returns an unexpected error.
    """
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            logger.info("Created bucket: %s", bucket_name)
        else:
            logger.debug("Bucket already exists: %s", bucket_name)
    except Exception:
        logger.exception("Failed to ensure bucket exists: %s", bucket_name)
        raise


# ---------------------------------------------------------------------------
# Upload helpers
# ---------------------------------------------------------------------------

def upload_dataframe_as_csv(
    client: "Minio",
    bucket_name: str,
    object_name: str,
    df: pd.DataFrame,
) -> None:
    """Serialize *df* to CSV and upload the bytes to MinIO.

    Parameters
    ----------
    client:
        An authenticated ``minio.Minio`` instance.
    bucket_name:
        Target bucket.
    object_name:
        Object key (path) inside the bucket.
    df:
        The DataFrame to upload.
    """
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)

    client.put_object(
        bucket_name,
        object_name,
        data=buffer,
        length=buffer.getbuffer().nbytes,
        content_type="text/csv",
    )
    logger.info(
        "Uploaded CSV (%d rows) -> s3://%s/%s",
        len(df),
        bucket_name,
        object_name,
    )


def upload_dataframe_as_parquet(
    client: "Minio",
    bucket_name: str,
    object_name: str,
    df: pd.DataFrame,
) -> None:
    """Serialize *df* to Parquet (via PyArrow) and upload to MinIO.

    Parameters
    ----------
    client:
        An authenticated ``minio.Minio`` instance.
    bucket_name:
        Target bucket.
    object_name:
        Object key (path) inside the bucket.
    df:
        The DataFrame to upload.
    """
    buffer = io.BytesIO()
    df.to_parquet(buffer, engine="pyarrow", index=False)
    buffer.seek(0)

    client.put_object(
        bucket_name,
        object_name,
        data=buffer,
        length=buffer.getbuffer().nbytes,
        content_type="application/octet-stream",
    )
    logger.info(
        "Uploaded Parquet (%d rows) -> s3://%s/%s",
        len(df),
        bucket_name,
        object_name,
    )


def upload_bytes(
    client: "Minio",
    bucket_name: str,
    object_name: str,
    data_bytes: bytes,
    content_type: str = "application/octet-stream",
) -> None:
    """Upload raw *data_bytes* to MinIO.

    Parameters
    ----------
    client:
        An authenticated ``minio.Minio`` instance.
    bucket_name:
        Target bucket.
    object_name:
        Object key (path) inside the bucket.
    data_bytes:
        Raw bytes to upload.
    content_type:
        MIME type of the payload.
    """
    buffer = io.BytesIO(data_bytes)

    client.put_object(
        bucket_name,
        object_name,
        data=buffer,
        length=len(data_bytes),
        content_type=content_type,
    )
    logger.info(
        "Uploaded %d bytes -> s3://%s/%s",
        len(data_bytes),
        bucket_name,
        object_name,
    )


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------

def download_to_bytes(
    client: "Minio",
    bucket_name: str,
    object_name: str,
) -> bytes:
    """Download an object from MinIO and return its contents as ``bytes``.

    Parameters
    ----------
    client:
        An authenticated ``minio.Minio`` instance.
    bucket_name:
        Source bucket.
    object_name:
        Object key (path) inside the bucket.

    Returns
    -------
    bytes
        The raw bytes of the object.
    """
    response = None
    try:
        response = client.get_object(bucket_name, object_name)
        data = response.read()
        logger.debug(
            "Downloaded %d bytes <- s3://%s/%s",
            len(data),
            bucket_name,
            object_name,
        )
        return data
    except Exception:
        logger.exception(
            "Failed to download s3://%s/%s", bucket_name, object_name
        )
        raise
    finally:
        if response is not None:
            response.close()
            response.release_conn()


def download_to_dataframe_csv(
    client: "Minio",
    bucket_name: str,
    object_name: str,
) -> pd.DataFrame:
    """Download a CSV object from MinIO and return it as a DataFrame.

    Parameters
    ----------
    client:
        An authenticated ``minio.Minio`` instance.
    bucket_name:
        Source bucket.
    object_name:
        Object key (path) inside the bucket.

    Returns
    -------
    pd.DataFrame
        The parsed DataFrame.
    """
    raw = download_to_bytes(client, bucket_name, object_name)
    df = pd.read_csv(io.BytesIO(raw))
    logger.info(
        "Parsed CSV DataFrame (%d rows, %d cols) <- s3://%s/%s",
        len(df),
        len(df.columns),
        bucket_name,
        object_name,
    )
    return df


def download_to_dataframe_parquet(
    client: "Minio",
    bucket_name: str,
    object_name: str,
) -> pd.DataFrame:
    """Download a Parquet object from MinIO and return it as a DataFrame.

    Parameters
    ----------
    client:
        An authenticated ``minio.Minio`` instance.
    bucket_name:
        Source bucket.
    object_name:
        Object key (path) inside the bucket.

    Returns
    -------
    pd.DataFrame
        The parsed DataFrame.
    """
    raw = download_to_bytes(client, bucket_name, object_name)
    df = pd.read_parquet(io.BytesIO(raw), engine="pyarrow")
    logger.info(
        "Parsed Parquet DataFrame (%d rows, %d cols) <- s3://%s/%s",
        len(df),
        len(df.columns),
        bucket_name,
        object_name,
    )
    return df


# ---------------------------------------------------------------------------
# Object introspection
# ---------------------------------------------------------------------------

def list_objects_with_prefix(
    client: "Minio",
    bucket_name: str,
    prefix: str,
) -> list[str]:
    """Return a list of object names under *prefix* in *bucket_name*.

    Parameters
    ----------
    client:
        An authenticated ``minio.Minio`` instance.
    bucket_name:
        Source bucket.
    prefix:
        Object key prefix to filter on.

    Returns
    -------
    list[str]
        Sorted list of matching object names.
    """
    objects = client.list_objects(bucket_name, prefix=prefix, recursive=True)
    names = sorted(obj.object_name for obj in objects)
    logger.debug(
        "Listed %d objects under s3://%s/%s",
        len(names),
        bucket_name,
        prefix,
    )
    return names


def object_exists(
    client: "Minio",
    bucket_name: str,
    object_name: str,
) -> bool:
    """Check whether *object_name* exists in *bucket_name*.

    Parameters
    ----------
    client:
        An authenticated ``minio.Minio`` instance.
    bucket_name:
        Source bucket.
    object_name:
        Object key to check.

    Returns
    -------
    bool
        ``True`` if the object exists, ``False`` otherwise.
    """
    try:
        client.stat_object(bucket_name, object_name)
        return True
    except Exception as exc:
        # minio raises S3Error with code "NoSuchKey" when not found.
        error_code = getattr(exc, "code", None)
        if error_code == "NoSuchKey":
            return False
        raise


def get_object_size(
    client: "Minio",
    bucket_name: str,
    object_name: str,
) -> int:
    """Return the size (in bytes) of *object_name* in *bucket_name*.

    Parameters
    ----------
    client:
        An authenticated ``minio.Minio`` instance.
    bucket_name:
        Source bucket.
    object_name:
        Object key to inspect.

    Returns
    -------
    int
        Size of the object in bytes.

    Raises
    ------
    minio.error.S3Error
        If the object does not exist or another server error occurs.
    """
    stat = client.stat_object(bucket_name, object_name)
    return stat.size
