import sys, os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config.settings import get_minio_client, get_duckdb_connection, MINIO_BUCKET_NAME, SILVER_PREFIX, GOLD_PREFIX
from src.utils.minio_client import ensure_bucket_exists, download_to_dataframe_parquet, upload_dataframe_as_parquet

def normalize_match_name(name):
    if pd.isna(name):
        return None
    return str(name).strip().lower()

def map_province_name(name, dim_prov_df):
    """Map BPS province names to WikiData province names/IDs."""
    if pd.isna(name):
        return None
        
    name = name.strip()
    name_key = normalize_match_name(name)
    
    # Common BPS/Wikidata naming differences.
    aliases = {
        'kepulauan bangka belitung': ['kepulauan bangka belitung', 'bangka belitung islands'],
        'dki jakarta': ['dki jakarta', 'jakarta'],
        'di yogyakarta': ['di yogyakarta', 'daerah istimewa yogyakarta', 'special region of yogyakarta', 'yogyakarta'],
        'nanggroe aceh darussalam': ['aceh'],
    }

    candidates = [name_key] + aliases.get(name_key, [])
    for candidate in candidates:
        match = dim_prov_df[
            (dim_prov_df['province_name_match'] == candidate) |
            (dim_prov_df['province_name_en_match'] == candidate)
        ]
        if not match.empty:
            return match.iloc[0]['province_id']

    print(f"Warning: Could not map province name '{name}'")
    return None

def build_gold_layer():
    try:
        client = get_minio_client()
        ensure_bucket_exists(client, MINIO_BUCKET_NAME)
        
        print(f"[{pd.Timestamp.now()}] Reading Silver data...")
        
        # 1. Read Silver Data
        df_prov_raw = download_to_dataframe_parquet(client, MINIO_BUCKET_NAME, f"{SILVER_PREFIX}wikidata_provinces/data.parquet")
        df_pdrb = download_to_dataframe_parquet(client, MINIO_BUCKET_NAME, f"{SILVER_PREFIX}bps_pdrb/data.parquet")
        df_pop = download_to_dataframe_parquet(client, MINIO_BUCKET_NAME, f"{SILVER_PREFIX}bps_populasi/data.parquet")
        
        # 2. Build dim_province
        print(f"[{pd.Timestamp.now()}] Building dim_province...")
        dim_province = df_prov_raw.copy()
        
        # Handle cases where column might not exist yet to prevent errors
        cols_to_keep = ['province_name_id', 'province_name_en', 'iso_code', 'capital_city', 
                        'area_km2', 'latitude', 'longitude', 'inception_date', 'wikidata_qid']
        
        # Filter only existing columns, rename province_name_id to province_name
        existing_cols = [c for c in cols_to_keep if c in dim_province.columns]
        dim_province = dim_province[existing_cols]
        if 'province_name_id' in dim_province.columns:
            dim_province = dim_province.rename(columns={'province_name_id': 'province_name'})

        # Keep current provinces only where Wikidata has ISO 3166-2 codes.
        if 'iso_code' in dim_province.columns:
            dim_province = dim_province[dim_province['iso_code'].notna()].copy()
            
        # Add surrogate key
        dim_province = dim_province.reset_index(drop=True)
        dim_province.insert(0, 'province_id', range(1, 1 + len(dim_province)))
        dim_province['province_name_match'] = dim_province.get('province_name', pd.Series(dtype=str)).apply(normalize_match_name)
        dim_province['province_name_en_match'] = dim_province.get('province_name_en', pd.Series(dtype=str)).apply(normalize_match_name)
        
        # 3. Build dim_year
        print(f"[{pd.Timestamp.now()}] Building dim_year...")
        years_pdrb = set(df_pdrb['year'].dropna().unique()) if 'year' in df_pdrb.columns else set()
        years_pop = set(df_pop['year'].dropna().unique()) if 'year' in df_pop.columns else set()
        all_years = sorted(list(years_pdrb.union(years_pop)))
        
        dim_year = pd.DataFrame({'year': all_years})
        if not dim_year.empty:
            dim_year.insert(0, 'year_id', range(1, 1 + len(dim_year)))
            dim_year['decade'] = (np.floor(dim_year['year'] / 10) * 10).astype(int).astype(str) + 's'
            dim_year['is_census_year'] = dim_year['year'].apply(lambda y: y % 10 == 0)
        
        # 4. Build dim_indicator
        print(f"[{pd.Timestamp.now()}] Building dim_indicator...")
        dim_indicator = pd.DataFrame([
            {'indicator_id': 1, 'indicator_name': 'GDP Current Price', 'indicator_type': 'economic', 'unit': 'Miliar Rupiah', 'description': 'Produk Domestik Regional Bruto Atas Dasar Harga Berlaku'},
            {'indicator_id': 2, 'indicator_name': 'GDP Constant Price', 'indicator_type': 'economic', 'unit': 'Miliar Rupiah', 'description': 'Produk Domestik Regional Bruto Atas Dasar Harga Konstan'},
            {'indicator_id': 3, 'indicator_name': 'Population', 'indicator_type': 'demographic', 'unit': 'Jiwa', 'description': 'Jumlah Penduduk'}
        ])
        
        # 5. Build fact_economics
        print(f"[{pd.Timestamp.now()}] Building fact_economics...")
        
        # Start with PDRB as base, outer join with Population
        fact_base = pd.merge(
            df_pdrb, 
            df_pop[['province_name', 'year', 'population']], 
            on=['province_name', 'year'], 
            how='outer'
        )
        
        # Map province to province_id
        fact_base['province_id'] = fact_base['province_name'].apply(lambda x: map_province_name(x, dim_province))
        
        # Map year to year_id
        if not dim_year.empty:
            year_map = dict(zip(dim_year['year'], dim_year['year_id']))
            fact_base['year_id'] = fact_base['year'].map(year_map)

        unmatched_provs = sorted(
            fact_base.loc[fact_base['province_id'].isna(), 'province_name']
            .dropna()
            .unique()
            .tolist()
        )
            
        # Drop rows where we couldn't map the core dimensions
        fact_base = fact_base.dropna(subset=['province_id', 'year_id'])
        fact_base['province_id'] = fact_base['province_id'].astype(int)
        fact_base['year_id'] = fact_base['year_id'].astype(int)
        
        # Compute GDP per capita (in Juta Rupiah)
        # gdp is in Miliar (10^9), pop is in Jiwa (10^0). 
        # (GDP * 1,000,000,000) / Pop = Rupiah. 
        # To get Juta (millions): (GDP * 1,000,000,000 / Pop) / 1,000,000 = (GDP * 1000) / Pop
        fact_base['gdp_per_capita'] = (fact_base['gdp_current_price'] * 1000) / fact_base['population']
        
        # Final columns
        fact_cols = ['province_id', 'year_id', 'gdp_current_price', 'gdp_constant_price', 'population', 'gdp_per_capita']
        fact_economics = fact_base[[c for c in fact_cols if c in fact_base.columns]].copy()
        fact_economics.insert(0, 'economics_id', range(1, 1 + len(fact_economics)))
        
        # 6. Upload Gold Parquet
        print(f"[{pd.Timestamp.now()}] Uploading Gold tables to MinIO...")
        upload_dataframe_as_parquet(client, MINIO_BUCKET_NAME, f"{GOLD_PREFIX}dim_province.parquet", dim_province)
        upload_dataframe_as_parquet(client, MINIO_BUCKET_NAME, f"{GOLD_PREFIX}dim_year.parquet", dim_year)
        upload_dataframe_as_parquet(client, MINIO_BUCKET_NAME, f"{GOLD_PREFIX}dim_indicator.parquet", dim_indicator)
        upload_dataframe_as_parquet(client, MINIO_BUCKET_NAME, f"{GOLD_PREFIX}fact_economics.parquet", fact_economics)
        
        # 7. Print Summary
        print(f"\n[{pd.Timestamp.now()}] Gold Transformation Summary:")
        print(f"  - dim_province: {len(dim_province)} rows")
        print(f"  - dim_year: {len(dim_year)} rows")
        print(f"  - dim_indicator: {len(dim_indicator)} rows")
        print(f"  - fact_economics: {len(fact_economics)} rows")
        
        if len(unmatched_provs) > 0:
            print(f"  - Unmatched provinces: {len(unmatched_provs)} -> {unmatched_provs}")
        else:
            print("  - All provinces matched successfully.")
            
        print("\nSample fact_economics data:")
        print(fact_economics.head())
        
    except Exception as e:
        import traceback
        print(f"[{pd.Timestamp.now()}] Gold transformation failed: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    build_gold_layer()
