import sys, os
import requests
import pandas as pd
from io import StringIO
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config.settings import get_minio_client, MINIO_BUCKET_NAME, BRONZE_PREFIX, WIKIDATA_SPARQL_ENDPOINT, WIKIDATA_USER_AGENT
from src.utils.minio_client import ensure_bucket_exists, upload_dataframe_as_csv, upload_bytes, object_exists
from src.utils.checksum import compute_dataframe_md5, get_stored_checksum, store_checksum, has_data_changed
from src.utils.metadata import create_ingestion_metadata, inject_metadata_columns, save_manifest

SPARQL_QUERY = """
SELECT
  ?province
  (STRAFTER(STR(?province), STR(wd:)) AS ?qid)
  ?nameID
  ?nameEN
  ?isoCode
  ?population
  ?populationDate
  ?area
  ?capitalLabel
  ?lat
  ?lon
  ?inception
WHERE {
  wd:Q252 wdt:P150 ?province .
  OPTIONAL { ?province rdfs:label ?nameID . FILTER(LANG(?nameID) = "id") }
  OPTIONAL { ?province rdfs:label ?nameEN . FILTER(LANG(?nameEN) = "en") }
  OPTIONAL { ?province wdt:P300 ?isoCode . }
  OPTIONAL { ?province wdt:P2046 ?area . }
  OPTIONAL { ?province wdt:P36 ?capital . }
  OPTIONAL {
    ?province wdt:P625 ?coords .
    BIND(geof:latitude(?coords) AS ?lat)
    BIND(geof:longitude(?coords) AS ?lon)
  }
  OPTIONAL { ?province wdt:P571 ?inception . }
  OPTIONAL {
    ?province p:P1082 ?popStatement .
    ?popStatement ps:P1082 ?population .
    ?popStatement pq:P585 ?populationDate .
    FILTER NOT EXISTS {
      ?province p:P1082 ?popStatement2 .
      ?popStatement2 pq:P585 ?populationDate2 .
      FILTER(?populationDate2 > ?populationDate)
    }
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "id,en". }
}
ORDER BY ?isoCode
"""

def fetch_wikidata_provinces():
    print(f"[{pd.Timestamp.now()}] Fetching data from WikiData SPARQL...")
    headers = {
        "User-Agent": WIKIDATA_USER_AGENT,
        "Accept": "application/sparql-results+json"
    }
    
    for attempt in range(3):
        try:
            response = requests.get(
                WIKIDATA_SPARQL_ENDPOINT, 
                params={"query": SPARQL_QUERY}, 
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # Parse JSON to DataFrame
            rows = []
            for item in data['results']['bindings']:
                row = {
                    'wikidata_qid': item.get('qid', {}).get('value'),
                    'province_name_id': item.get('nameID', {}).get('value'),
                    'province_name_en': item.get('nameEN', {}).get('value'),
                    'iso_code': item.get('isoCode', {}).get('value'),
                    'population': item.get('population', {}).get('value'),
                    'population_date': item.get('populationDate', {}).get('value'),
                    'area_km2': item.get('area', {}).get('value'),
                    'capital_city': item.get('capitalLabel', {}).get('value'),
                    'latitude': item.get('lat', {}).get('value'),
                    'longitude': item.get('lon', {}).get('value'),
                    'inception_date': item.get('inception', {}).get('value'),
                }
                rows.append(row)
                
            df = pd.DataFrame(rows)
            print(f"[{pd.Timestamp.now()}] Successfully fetched {len(df)} records from WikiData.")
            if len(df) == 0:
                print(f"[{pd.Timestamp.now()}] Warning: 0 records fetched. The SPARQL query might have returned empty results.")
                # We can choose to return an empty df, but it's better to treat it as a failure to prevent wiping data.
                raise ValueError("WikiData API returned 0 records.")
                
            return df
            
        except Exception as e:
            print(f"[{pd.Timestamp.now()}] Error on attempt {attempt+1}: {e}")
            if attempt < 2:
                time.sleep(5)
            else:
                raise

def main():
    try:
        client = get_minio_client()
        ensure_bucket_exists(client, MINIO_BUCKET_NAME)
        
        try:
            df = fetch_wikidata_provinces()
        except Exception as api_err:
            print(f"[{pd.Timestamp.now()}] Warning: {api_err}. Using fallback local WikiData CSV...")
            fallback_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'seed', 'wikidata_provinces_fallback.csv')
            df = pd.read_csv(fallback_path)
            print(f"[{pd.Timestamp.now()}] Successfully loaded {len(df)} records from fallback.")
        
        # Idempotency check
        checksum_path = f"{BRONZE_PREFIX}wikidata/provinces/_checksums/latest.md5"
        new_checksum = compute_dataframe_md5(df)
        
        if not has_data_changed(client, MINIO_BUCKET_NAME, checksum_path, new_checksum):
            print(f"[{pd.Timestamp.now()}] No changes detected in WikiData source. Skipping ingestion.")
            return
            
        print(f"[{pd.Timestamp.now()}] Changes detected. Proceeding with ingestion...")
        
        # Inject metadata
        record_count = len(df)
        metadata = create_ingestion_metadata(
            source_name='WikiData',
            source_url=WIKIDATA_SPARQL_ENDPOINT,
            api_version='sparql_v1',
            operator_id='pipeline_auto',
            record_count=record_count,
            data_format='CSV'
        )
        
        df_with_meta = inject_metadata_columns(df.copy(), metadata)
        
        timestamp_str = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        manifest_path = f"{BRONZE_PREFIX}wikidata/provinces/_manifest/manifest_{timestamp_str}.json"
        
        save_manifest(client, MINIO_BUCKET_NAME, manifest_path, metadata)
        print(f"[{pd.Timestamp.now()}] Saved metadata manifest to {manifest_path}")
        
        # Upload data
        historical_path = f"{BRONZE_PREFIX}wikidata/provinces/provinces_{timestamp_str}.csv"
        latest_path = f"{BRONZE_PREFIX}wikidata/provinces/latest.csv"
        
        upload_dataframe_as_csv(client, MINIO_BUCKET_NAME, historical_path, df_with_meta)
        upload_dataframe_as_csv(client, MINIO_BUCKET_NAME, latest_path, df_with_meta)
        print(f"[{pd.Timestamp.now()}] Uploaded data to {historical_path} and {latest_path}")
        
        # Update checksum
        store_checksum(client, MINIO_BUCKET_NAME, checksum_path, new_checksum)
        print(f"[{pd.Timestamp.now()}] Updated checksum at {checksum_path}")
        
        print(f"[{pd.Timestamp.now()}] WikiData ingestion completed successfully.")
        
    except Exception as e:
        print(f"[{pd.Timestamp.now()}] WikiData ingestion failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
