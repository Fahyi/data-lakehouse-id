"""Delta Lake-style versioning for the Data Lakehouse platform.

This module implements a lightweight transaction log inspired by the
Delta Lake protocol.  Each mutation to a dataset is recorded as a
numbered JSON entry under ``_delta_log/``, and the previous data file
is copied to ``_versions/`` for point-in-time recovery.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING

from src.utils.minio_client import (
    download_to_bytes,
    list_objects_with_prefix,
    object_exists,
    upload_bytes,
)

if TYPE_CHECKING:
    from minio import Minio

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class DeltaLogEntry:
    """A single entry in the delta transaction log.

    Attributes
    ----------
    version:
        Monotonically increasing version number (0-based).
    timestamp:
        ISO-8601 timestamp when the operation was performed.
    operation:
        Short label such as ``"WRITE"``, ``"OVERWRITE"``, or ``"MERGE"``.
    operation_parameters:
        Free-form dict of parameters passed to the operation.
    added_files:
        List of object keys that were added in this version.
    removed_files:
        List of object keys that were removed in this version.
    num_records:
        Total number of records written by this operation.
    schema:
        Dict representing the dataset schema (e.g. column name → dtype).
    checksum:
        MD5 digest of the data payload at this version.
    """

    version: int
    timestamp: str
    operation: str
    operation_parameters: dict = field(default_factory=dict)
    added_files: list[str] = field(default_factory=list)
    removed_files: list[str] = field(default_factory=list)
    num_records: int = 0
    schema: dict = field(default_factory=dict)
    checksum: str = ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _log_prefix(delta_log_prefix: str) -> str:
    """Return the ``_delta_log/`` path under *delta_log_prefix*."""
    return f"{delta_log_prefix}/_delta_log"


def _versions_prefix(delta_log_prefix: str) -> str:
    """Return the ``_versions/`` path under *delta_log_prefix*."""
    return f"{delta_log_prefix}/_versions"


def _entry_object_name(delta_log_prefix: str, version: int) -> str:
    """Return the object key for a given version's log entry JSON."""
    return f"{_log_prefix(delta_log_prefix)}/{version:08d}.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_current_version(
    client: "Minio",
    bucket_name: str,
    delta_log_prefix: str,
) -> int:
    """Determine the latest version recorded in the delta log.

    Scans the ``_delta_log/`` prefix and returns the highest version
    number found.  If no log entries exist, returns ``-1``.

    Parameters
    ----------
    client:
        An authenticated ``minio.Minio`` instance.
    bucket_name:
        The bucket that holds the delta log.
    delta_log_prefix:
        Base object-key prefix (e.g. ``"bronze/earthquakes"``).

    Returns
    -------
    int
        Latest version number, or ``-1`` if no entries exist.
    """
    log_dir = _log_prefix(delta_log_prefix)
    entries = list_objects_with_prefix(client, bucket_name, f"{log_dir}/")

    if not entries:
        logger.debug("No delta log entries under s3://%s/%s/", bucket_name, log_dir)
        return -1

    # Extract version numbers from filenames like "00000003.json"
    versions: list[int] = []
    for name in entries:
        filename = name.rsplit("/", 1)[-1]
        if filename.endswith(".json"):
            try:
                versions.append(int(filename.replace(".json", "")))
            except ValueError:
                logger.warning("Skipping non-numeric log entry: %s", name)

    if not versions:
        return -1

    current = max(versions)
    logger.debug("Current delta log version: %d", current)
    return current


def write_delta_log(
    client: "Minio",
    bucket_name: str,
    delta_log_prefix: str,
    entry: DeltaLogEntry,
) -> None:
    """Persist a ``DeltaLogEntry`` as a numbered JSON file in MinIO.

    The entry is stored at
    ``{delta_log_prefix}/_delta_log/{version:08d}.json``.

    Parameters
    ----------
    client:
        An authenticated ``minio.Minio`` instance.
    bucket_name:
        The target bucket.
    delta_log_prefix:
        Base object-key prefix.
    entry:
        The log entry to write.
    """
    object_name = _entry_object_name(delta_log_prefix, entry.version)
    payload = json.dumps(asdict(entry), indent=2, ensure_ascii=False)

    upload_bytes(
        client,
        bucket_name,
        object_name,
        payload.encode("utf-8"),
        content_type="application/json",
    )
    logger.info(
        "Wrote delta log v%d -> s3://%s/%s",
        entry.version,
        bucket_name,
        object_name,
    )


def read_delta_log(
    client: "Minio",
    bucket_name: str,
    delta_log_prefix: str,
) -> list[DeltaLogEntry]:
    """Read all delta log entries and return them sorted by version.

    Parameters
    ----------
    client:
        An authenticated ``minio.Minio`` instance.
    bucket_name:
        The bucket that holds the delta log.
    delta_log_prefix:
        Base object-key prefix.

    Returns
    -------
    list[DeltaLogEntry]
        All entries sorted ascending by version.
    """
    log_dir = _log_prefix(delta_log_prefix)
    names = list_objects_with_prefix(client, bucket_name, f"{log_dir}/")

    entries: list[DeltaLogEntry] = []
    for name in names:
        if not name.endswith(".json"):
            continue
        try:
            raw = download_to_bytes(client, bucket_name, name)
            data = json.loads(raw.decode("utf-8"))
            entries.append(DeltaLogEntry(**data))
        except Exception:
            logger.exception("Failed to parse delta log entry: %s", name)

    entries.sort(key=lambda e: e.version)
    logger.info(
        "Read %d delta log entries from s3://%s/%s/",
        len(entries),
        bucket_name,
        log_dir,
    )
    return entries


def create_versioned_backup(
    client: "Minio",
    bucket_name: str,
    data_path: str,
    version: int,
    delta_log_prefix: str | None = None,
) -> str | None:
    """Copy the current data file to a versioned backup location.

    The backup is stored at
    ``{delta_log_prefix}/_versions/data_v{version}.parquet``.
    If *delta_log_prefix* is not provided, it is derived by stripping
    the filename from *data_path*.

    Parameters
    ----------
    client:
        An authenticated ``minio.Minio`` instance.
    bucket_name:
        The bucket containing the data file.
    data_path:
        Object key of the current data file (e.g.
        ``"bronze/earthquakes/data.parquet"``).
    version:
        Version number to tag the backup with.
    delta_log_prefix:
        Optional explicit prefix.  Defaults to the directory part of
        *data_path*.

    Returns
    -------
    str | None
        The object key of the backup, or ``None`` if the source file
        does not exist.
    """
    if not object_exists(client, bucket_name, data_path):
        logger.warning(
            "Source file does not exist for backup: s3://%s/%s",
            bucket_name,
            data_path,
        )
        return None

    if delta_log_prefix is None:
        # Derive prefix from data_path: "bronze/earthquakes/data.parquet" → "bronze/earthquakes"
        delta_log_prefix = data_path.rsplit("/", 1)[0] if "/" in data_path else ""

    backup_name = (
        f"{_versions_prefix(delta_log_prefix)}/data_v{version}.parquet"
    )

    # Read source and re-upload to the backup location.
    data = download_to_bytes(client, bucket_name, data_path)
    upload_bytes(
        client,
        bucket_name,
        backup_name,
        data,
        content_type="application/octet-stream",
    )
    logger.info(
        "Created versioned backup v%d -> s3://%s/%s",
        version,
        bucket_name,
        backup_name,
    )
    return backup_name
