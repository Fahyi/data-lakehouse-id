import sys, os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config.settings import get_minio_client, get_duckdb_connection, MINIO_BUCKET_NAME, BRONZE_PREFIX, SILVER_PREFIX
from src.utils.minio_client import ensure_bucket_exists, download_to_dataframe_csv, upload_dataframe_as_parquet, object_exists
from src.utils.delta_log import DeltaLogEntry, get_current_version, write_delta_log, create_versioned_backup
from src.utils.checksum import compute_dataframe_md5

def clean_string_cols(df):
    """Strip whitespace and handle 'NA', 'NULL' strings"""
    str_cols = df.select_dtypes(include=['object', 'string']).columns
    for col in str_cols:
        df[col] = df[col].astype(str).str.strip()
        df.loc[df[col].isin(['NA', 'NULL', 'None', '', 'nan']), col] = None
    return df

def normalize_province_name(name):
    if not isinstance(name, str):
        return name
    name = name.strip()
    mapping = {
        'D.I. Yogyakarta': 'DI Yogyakarta',
        'D.I Yogyakarta': 'DI Yogyakarta',
        'Daerah Istimewa Yogyakarta': 'DI Yogyakarta',
        'D.K.I. Jakarta': 'DKI Jakarta',
        'D.K.I Jakarta': 'DKI Jakarta',
        'Daerah Khusus Ibukota Jakarta': 'DKI Jakarta',
        'Bangka Belitung': 'Kepulauan Bangka Belitung'
    }
    return mapping.get(name, name)

def fix_indonesian_numbers(val):
    if pd.isna(val):
        return val
    if isinstance(val, str):
        # Remove thousands separators (dots) but keep decimals (commas replaced with dots if any)
        # Assuming format like "1.234.567" for millions
        val = val.replace('.', '')
        # If there are comma decimals, replace with dot
        val = val.replace(',', '.')
    try:
        return float(val)
    except ValueError:
        return np.nan

def process_and_save(client, df, table_name, output_path):
    print(f"[{pd.Timestamp.now()}] Saving Silver table '{table_name}'...")
    
    # Delta log setup
    delta_log_prefix = f"{SILVER_PREFIX}{table_name}"
    current_version = get_current_version(client, MINIO_BUCKET_NAME, delta_log_prefix)
    new_version = current_version + 1
    
    # Backup existing if present
    create_versioned_backup(client, MINIO_BUCKET_NAME, output_path, current_version)
    
    # Upload new Parquet
    upload_dataframe_as_parquet(client, MINIO_BUCKET_NAME, output_path, df)
    
    # Write delta log entry
    schema_info = {col: str(dtype) for col, dtype in df.dtypes.items()}
    new_checksum = compute_dataframe_md5(df)
    
    entry = DeltaLogEntry(
        version=new_version,
        timestamp=pd.Timestamp.now('UTC').isoformat(),
        operation='WRITE',
        operation_parameters={'mode': 'Overwrite'},
        added_files=['data.parquet'],
        removed_files=[],
        num_records=len(df),
        schema=schema_info,
        checksum=new_checksum
    )
    
    write_delta_log(client, MINIO_BUCKET_NAME, delta_log_prefix, entry)
    print(f"[{pd.Timestamp.now()}] Saved {table_name} version {new_version} with {len(df)} records.")


def clean_wikidata(client):
    print(f"[{pd.Timestamp.now()}] Cleaning WikiData Provinces...")
    path = f"{BRONZE_PREFIX}wikidata/provinces/latest.csv"
    if not object_exists(client, MINIO_BUCKET_NAME, path):
        print(f"Error: {path} not found.")
        return
        
    df = download_to_dataframe_csv(client, MINIO_BUCKET_NAME, path)
    original_count = len(df)
    
    # Drop bronze metadata
    meta_cols = ['ingestion_timestamp', 'source_name', 'operator_id']
    df = df.drop(columns=[c for c in meta_cols if c in df.columns], errors='ignore')
    
    df = clean_string_cols(df)
    
    # Cast types if columns exist
    if 'population' in df.columns:
        df['population'] = pd.to_numeric(df['population'], errors='coerce').astype('Int64')
    if 'area_km2' in df.columns:
        df['area_km2'] = pd.to_numeric(df['area_km2'], errors='coerce').astype(float)
    if 'latitude' in df.columns:
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce').astype(float)
    if 'longitude' in df.columns:
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce').astype(float)
    
    # Deduplicate by QID
    if 'wikidata_qid' in df.columns:
        df = df.drop_duplicates(subset=['wikidata_qid'], keep='first')
        
    print(f"[{pd.Timestamp.now()}] Cleaned WikiData: {original_count} -> {len(df)} records.")
    
    output_path = f"{SILVER_PREFIX}wikidata_provinces/data.parquet"
    process_and_save(client, df, 'wikidata_provinces', output_path)

def clean_pdrb(client):
    print(f"[{pd.Timestamp.now()}] Cleaning BPS PDRB...")
    path = f"{BRONZE_PREFIX}bps/pdrb/latest.csv"
    if not object_exists(client, MINIO_BUCKET_NAME, path):
        print(f"Error: {path} not found.")
        return
        
    df = download_to_dataframe_csv(client, MINIO_BUCKET_NAME, path)
    
    meta_cols = ['ingestion_timestamp', 'source_name', 'operator_id']
    df = df.drop(columns=[c for c in meta_cols if c in df.columns], errors='ignore')
    
    df = clean_string_cols(df)
    
    if 'nama_provinsi' in df.columns:
        df['nama_provinsi'] = df['nama_provinsi'].apply(normalize_province_name)
        
    if 'pdrb_harga_berlaku' in df.columns:
        df['pdrb_harga_berlaku'] = df['pdrb_harga_berlaku'].apply(fix_indonesian_numbers)
    if 'pdrb_harga_konstan' in df.columns:
        df['pdrb_harga_konstan'] = df['pdrb_harga_konstan'].apply(fix_indonesian_numbers)
        
    df['kode_provinsi'] = pd.to_numeric(df['kode_provinsi'], errors='coerce').astype('Int64')
    df['tahun'] = pd.to_numeric(df['tahun'], errors='coerce').astype('Int64')
    
    df = df.drop(columns=['satuan'], errors='ignore')
    
    # Rename to English
    rename_map = {
        'kode_provinsi': 'province_code',
        'nama_provinsi': 'province_name',
        'tahun': 'year',
        'pdrb_harga_berlaku': 'gdp_current_price',
        'pdrb_harga_konstan': 'gdp_constant_price'
    }
    df = df.rename(columns=rename_map)
    
    output_path = f"{SILVER_PREFIX}bps_pdrb/data.parquet"
    process_and_save(client, df, 'bps_pdrb', output_path)

def clean_populasi(client):
    print(f"[{pd.Timestamp.now()}] Cleaning BPS Populasi...")
    path = f"{BRONZE_PREFIX}bps/populasi/latest.csv"
    if not object_exists(client, MINIO_BUCKET_NAME, path):
        print(f"Error: {path} not found.")
        return
        
    df = download_to_dataframe_csv(client, MINIO_BUCKET_NAME, path)
    
    meta_cols = ['ingestion_timestamp', 'source_name', 'operator_id']
    df = df.drop(columns=[c for c in meta_cols if c in df.columns], errors='ignore')
    
    df = clean_string_cols(df)
    
    if 'nama_provinsi' in df.columns:
        df['nama_provinsi'] = df['nama_provinsi'].apply(normalize_province_name)
        
    if 'jumlah_penduduk' in df.columns:
        df['jumlah_penduduk'] = df['jumlah_penduduk'].apply(fix_indonesian_numbers).astype('Int64')
        
    df['kode_provinsi'] = pd.to_numeric(df['kode_provinsi'], errors='coerce').astype('Int64')
    df['tahun'] = pd.to_numeric(df['tahun'], errors='coerce').astype('Int64')
    
    df = df.drop(columns=['satuan'], errors='ignore')
    
    rename_map = {
        'kode_provinsi': 'province_code',
        'nama_provinsi': 'province_name',
        'tahun': 'year',
        'jumlah_penduduk': 'population'
    }
    df = df.rename(columns=rename_map)
    
    output_path = f"{SILVER_PREFIX}bps_populasi/data.parquet"
    process_and_save(client, df, 'bps_populasi', output_path)

def main():
    try:
        client = get_minio_client()
        ensure_bucket_exists(client, MINIO_BUCKET_NAME)
        
        clean_wikidata(client)
        clean_pdrb(client)
        clean_populasi(client)
        
        print(f"[{pd.Timestamp.now()}] Silver transformation completed successfully.")
        
    except Exception as e:
        print(f"[{pd.Timestamp.now()}] Silver transformation failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
