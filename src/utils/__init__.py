# src.utils package — Utility modules for the Data Lakehouse platform.

from src.utils.minio_client import (
    ensure_bucket_exists,
    upload_dataframe_as_csv,
    upload_dataframe_as_parquet,
    upload_bytes,
    download_to_bytes,
    download_to_dataframe_csv,
    download_to_dataframe_parquet,
    list_objects_with_prefix,
    object_exists,
    get_object_size,
)
from src.utils.checksum import (
    compute_md5,
    compute_dataframe_md5,
    get_stored_checksum,
    store_checksum,
    has_data_changed,
)
from src.utils.delta_log import (
    DeltaLogEntry,
    get_current_version,
    write_delta_log,
    read_delta_log,
    create_versioned_backup,
)
from src.utils.metadata import (
    create_ingestion_metadata,
    inject_metadata_columns,
    save_manifest,
    load_manifest,
)

__all__ = [
    # minio_client
    "ensure_bucket_exists",
    "upload_dataframe_as_csv",
    "upload_dataframe_as_parquet",
    "upload_bytes",
    "download_to_bytes",
    "download_to_dataframe_csv",
    "download_to_dataframe_parquet",
    "list_objects_with_prefix",
    "object_exists",
    "get_object_size",
    # checksum
    "compute_md5",
    "compute_dataframe_md5",
    "get_stored_checksum",
    "store_checksum",
    "has_data_changed",
    # delta_log
    "DeltaLogEntry",
    "get_current_version",
    "write_delta_log",
    "read_delta_log",
    "create_versioned_backup",
    # metadata
    "create_ingestion_metadata",
    "inject_metadata_columns",
    "save_manifest",
    "load_manifest",
]
