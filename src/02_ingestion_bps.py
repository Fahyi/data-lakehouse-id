import sys
import os
import io
import time
import requests
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config.settings import get_minio_client, MINIO_BUCKET_NAME, BRONZE_PREFIX
from src.utils.minio_client import ensure_bucket_exists, upload_dataframe_as_csv
from src.utils.checksum import compute_dataframe_md5, get_stored_checksum, store_checksum, has_data_changed
from src.utils.metadata import create_ingestion_metadata, inject_metadata_columns, save_manifest

PDRB_API_KEY = os.getenv("BPS_API_KEY", "ceac3a2db682876b28da1fe7bd80b58d")
POP_API_KEY = os.getenv("BPS_API_KEY", "ceac3a2db682876b28da1fe7bd80b58d")


def parse_bps_number(value):
    """Parse BPS Indonesian-formatted numbers, e.g. '15.386,6' -> 15386.6."""
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    value = str(value).strip()
    if value in {"", "-", "–", "...", "NA"}:
        return None

    try:
        return float(value.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def normalize_bps_province_name(name):
    """Normalize common BPS province labels while preserving acronyms."""
    if not isinstance(name, str):
        return name

    normalized = name.strip()
    upper_name = normalized.upper()
    special_names = {
        "DKI JAKARTA": "DKI Jakarta",
        "D.K.I. JAKARTA": "DKI Jakarta",
        "DI YOGYAKARTA": "DI Yogyakarta",
        "D.I. YOGYAKARTA": "DI Yogyakarta",
        "KEP. BANGKA BELITUNG": "Kepulauan Bangka Belitung",
        "KEPULAUAN BANGKA BELITUNG": "Kepulauan Bangka Belitung",
        "KEP. RIAU": "Kepulauan Riau",
        "NANGGROE ACEH DARUSSALAM": "Aceh",
    }
    return special_names.get(upper_name, normalized.title())

def fetch_pdrb_data():
    records = []
    # th_id map for years 2019 to 2023
    year_map = {119: 2019, 120: 2020, 121: 2021, 122: 2022, 123: 2023}
    
    for th_id, year in year_map.items():
        url = f"https://webapi.bps.go.id/v1/api/list/model/data/lang/ind/domain/0000/var/286/th/{th_id}/key/{PDRB_API_KEY}"
        print(f"Fetching PDRB data for {year}...")
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                d = resp.json()
                if 'datacontent' not in d:
                    print(f"No datacontent for {year}")
                    continue
                vervars = {str(item['val']): item['label'] for item in d.get('vervar', [])}
                turvars = {str(item['val']): item['label'] for item in d.get('turvar', [])}
                
                for key, value in d['datacontent'].items():
                    # Current BPS key format for this table:
                    # {vervar 4 digit}{var 3 digit}{turvar 3 digit}{tahun 3 digit}{turtahun 1 digit}
                    key = str(key)
                    if len(key) < 14:
                        continue

                    vervar = key[:4]
                    turvar = key[7:10]

                    if turvar not in turvars:
                        continue

                    prov_name = vervars.get(vervar)
                    if prov_name and prov_name.upper() != 'INDONESIA':
                        records.append({
                            'kode_provinsi': vervar,
                            'nama_provinsi': normalize_bps_province_name(prov_name),
                            'tahun': year,
                            'turvar': turvar,
                            'nilai': value
                        })
            else:
                print(f"Failed to fetch {year}: {resp.status_code}")
        except Exception as e:
            print(f"Error fetching PDRB for {year}: {e}")
        time.sleep(1) # Be nice to BPS API

    df = pd.DataFrame(records)
    if df.empty:
        return df
        
    df = df.pivot_table(index=['kode_provinsi', 'nama_provinsi', 'tahun'], columns='turvar', values='nilai').reset_index()
    df.columns.name = None
    df.rename(columns={530: 'pdrb_harga_berlaku', 531: 'pdrb_harga_konstan',
                       '530': 'pdrb_harga_berlaku', '531': 'pdrb_harga_konstan'}, inplace=True)
    return df

def fetch_pop_data():
    records = []
    years = [2019, 2020, 2021, 2022, 2023]
    
    for year in years:
        url = f"https://webapi.bps.go.id/v1/api/interoperabilitas/datasource/simdasi/id/25/tahun/{year}/id_tabel/WVRlTTcySlZDa3lUcFp6czNwbHl4QT09/wilayah/0000000/key/{POP_API_KEY}"
        print(f"Fetching Population data for {year}...")
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                d = resp.json()
                data_arr = d.get('data', [])
                if len(data_arr) > 1 and 'data' in data_arr[1]:
                    payload = data_arr[1]
                    population_var = None
                    for var_id, meta in payload.get('kolom', {}).items():
                        var_name = str(meta.get('nama_variabel', '')).lower()
                        if 'jumlah penduduk' in var_name:
                            population_var = var_id
                            break

                    if not population_var:
                        print(f"Population variable not found for {year}")
                        continue

                    for row in payload['data']:
                        prov_code_raw = row.get('kode_wilayah')
                        prov_name = row.get('label')
                        variables = row.get('variables', {})
                        val_str = variables.get(population_var, {}).get('value_raw')

                        if not prov_code_raw or not prov_name or not val_str:
                            continue

                        prov_code = str(prov_code_raw)[:2] + "00"
                        if prov_code == "0000" or prov_name.upper() == "INDONESIA":
                            continue

                        # BPS population values are in thousands ("ribu").
                        val_float = parse_bps_number(val_str)
                        if val_float is None:
                            continue

                        records.append({
                            'kode_provinsi': prov_code,
                            'nama_provinsi': normalize_bps_province_name(prov_name),
                            'tahun': year,
                            'jumlah_penduduk': int(round(val_float * 1000))
                        })
            else:
                print(f"Failed to fetch population {year}: {resp.status_code}")
        except Exception as e:
            print(f"Error fetching Population for {year}: {e}")
        time.sleep(1)
        
    df = pd.DataFrame(records)
    return df

def main():
    print("[Ingestion] Starting live BPS API ingestion...")
    client = get_minio_client()
    ensure_bucket_exists(client, MINIO_BUCKET_NAME)
    
    # 1. PDRB Data
    print("=== PDRB DATA ===")
    df_pdrb = fetch_pdrb_data()
    print(f"Fetched {len(df_pdrb)} PDRB records.")
    
    if not df_pdrb.empty:
        md5_pdrb = compute_dataframe_md5(df_pdrb)
        checksum_path_pdrb = f"{BRONZE_PREFIX}bps/pdrb/_checksums/latest.md5"
        
        if has_data_changed(client, MINIO_BUCKET_NAME, checksum_path_pdrb, md5_pdrb):
            print("PDRB data changed. Uploading to Bronze...")
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            meta_pdrb = create_ingestion_metadata("BPS_PDRB_API", "webapi.bps.go.id", "v1", "pipeline_auto", len(df_pdrb), "csv")
            df_pdrb_meta = inject_metadata_columns(df_pdrb, meta_pdrb)
            
            upload_dataframe_as_csv(client, MINIO_BUCKET_NAME, f"{BRONZE_PREFIX}bps/pdrb/pdrb_{timestamp}.csv", df_pdrb_meta)
            upload_dataframe_as_csv(client, MINIO_BUCKET_NAME, f"{BRONZE_PREFIX}bps/pdrb/latest.csv", df_pdrb_meta)
            
            save_manifest(client, MINIO_BUCKET_NAME, f"{BRONZE_PREFIX}bps/pdrb/_manifest/manifest_{timestamp}.json", meta_pdrb)
            store_checksum(client, MINIO_BUCKET_NAME, checksum_path_pdrb, md5_pdrb)
            print("PDRB successfully uploaded.")
        else:
            print("PDRB data unchanged. Skipping upload.")
            
    # 2. Population Data
    print("\n=== POPULATION DATA ===")
    df_pop = fetch_pop_data()
    print(f"Fetched {len(df_pop)} Population records.")
    
    if not df_pop.empty:
        md5_pop = compute_dataframe_md5(df_pop)
        checksum_path_pop = f"{BRONZE_PREFIX}bps/populasi/_checksums/latest.md5"
        
        if has_data_changed(client, MINIO_BUCKET_NAME, checksum_path_pop, md5_pop):
            print("Population data changed. Uploading to Bronze...")
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            meta_pop = create_ingestion_metadata("BPS_SIMDASI_API", "webapi.bps.go.id", "v1", "pipeline_auto", len(df_pop), "csv")
            df_pop_meta = inject_metadata_columns(df_pop, meta_pop)
            
            upload_dataframe_as_csv(client, MINIO_BUCKET_NAME, f"{BRONZE_PREFIX}bps/populasi/populasi_{timestamp}.csv", df_pop_meta)
            upload_dataframe_as_csv(client, MINIO_BUCKET_NAME, f"{BRONZE_PREFIX}bps/populasi/latest.csv", df_pop_meta)
            
            save_manifest(client, MINIO_BUCKET_NAME, f"{BRONZE_PREFIX}bps/populasi/_manifest/manifest_{timestamp}.json", meta_pop)
            store_checksum(client, MINIO_BUCKET_NAME, checksum_path_pop, md5_pop)
            print("Population successfully uploaded.")
        else:
            print("Population data unchanged. Skipping upload.")
            
    print("\n[Ingestion] Completed.")

if __name__ == '__main__':
    main()
