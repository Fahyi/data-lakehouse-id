import sys, os
import time
import duckdb
import pandas as pd
from tabulate import tabulate

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config.settings import get_minio_client, MINIO_BUCKET_NAME, BRONZE_PREFIX, SILVER_PREFIX, GOLD_PREFIX
from src.utils.minio_client import get_object_size, download_to_bytes

def benchmark_read(file_bytes, is_parquet=False):
    """Benchmark DuckDB read speed from bytes (simulated local read)."""
    con = duckdb.connect(':memory:')
    start_time = time.perf_counter()
    if is_parquet:
        # For parquet from bytes in memory, we need a temp file or via pandas if small
        # The easiest pure DuckDB way for a benchmark from bytes is writing temp file
        temp_path = '/tmp/bench.parquet'
        with open(temp_path, 'wb') as f:
            f.write(file_bytes)
        con.execute(f"SELECT COUNT(*) FROM read_parquet('{temp_path}')").fetchone()
        if os.path.exists(temp_path):
            os.remove(temp_path)
    else:
        temp_path = '/tmp/bench.csv'
        with open(temp_path, 'wb') as f:
            f.write(file_bytes)
        con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{temp_path}')").fetchone()
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
    end_time = time.perf_counter()
    return (end_time - start_time) * 1000  # Return in ms

def run_comparison():
    print(f"[{pd.Timestamp.now()}] Running File Format Comparison (Bonus +5%)...\n")
    client = get_minio_client()
    
    datasets = [
        {
            "name": "WikiData Provinces",
            "bronze": f"{BRONZE_PREFIX}wikidata/provinces/latest.csv",
            "silver": f"{SILVER_PREFIX}wikidata_provinces/data.parquet",
            "gold": f"{GOLD_PREFIX}dim_province.parquet"
        },
        {
            "name": "BPS PDRB (GDP)",
            "bronze": f"{BRONZE_PREFIX}bps/pdrb/latest.csv",
            "silver": f"{SILVER_PREFIX}bps_pdrb/data.parquet",
            "gold": f"{GOLD_PREFIX}fact_economics.parquet" # Approx comparison
        },
        {
            "name": "BPS Populasi",
            "bronze": f"{BRONZE_PREFIX}bps/populasi/latest.csv",
            "silver": f"{SILVER_PREFIX}bps_populasi/data.parquet",
            "gold": None # Merged into fact_economics
        }
    ]
    
    results = []
    
    for ds in datasets:
        row = {"Dataset": ds["name"]}
        
        # Bronze CSV
        try:
            b_size = get_object_size(client, MINIO_BUCKET_NAME, ds["bronze"])
            b_bytes = download_to_bytes(client, MINIO_BUCKET_NAME, ds["bronze"])
            b_time = benchmark_read(b_bytes, is_parquet=False)
            row["Bronze CSV (KB)"] = f"{b_size / 1024:.2f}"
            row["CSV Read (ms)"] = f"{b_time:.2f}"
        except Exception:
            row["Bronze CSV (KB)"] = "N/A"
            row["CSV Read (ms)"] = "N/A"
            b_size = 0
            
        # Silver Parquet
        try:
            s_size = get_object_size(client, MINIO_BUCKET_NAME, ds["silver"])
            s_bytes = download_to_bytes(client, MINIO_BUCKET_NAME, ds["silver"])
            s_time = benchmark_read(s_bytes, is_parquet=True)
            row["Silver Parquet (KB)"] = f"{s_size / 1024:.2f}"
            row["Parquet Read (ms)"] = f"{s_time:.2f}"
        except Exception:
            row["Silver Parquet (KB)"] = "N/A"
            row["Parquet Read (ms)"] = "N/A"
            s_size = 0
            s_time = 0
            
        # Gold Parquet
        if ds["gold"]:
            try:
                g_size = get_object_size(client, MINIO_BUCKET_NAME, ds["gold"])
                row["Gold Parquet (KB)"] = f"{g_size / 1024:.2f}"
            except Exception:
                row["Gold Parquet (KB)"] = "N/A"
        else:
             row["Gold Parquet (KB)"] = "-"
             
        # Metrics
        if b_size > 0 and s_size > 0:
            row["Compression Ratio"] = f"{b_size / s_size:.1f}x"
        else:
            row["Compression Ratio"] = "N/A"
            
        if b_size > 0 and s_size > 0 and 'b_time' in locals() and s_time > 0:
            row["Speed Improvement"] = f"{b_time / s_time:.1f}x"
        else:
            row["Speed Improvement"] = "N/A"
            
        results.append(row)
        
    print("FILE FORMAT STORAGE & PERFORMANCE COMPARISON:")
    print(tabulate(results, headers="keys", tablefmt="pretty"))
    
    print("\nKESIMPULAN (CONCLUSIONS):")
    print("1. Efisiensi Penyimpanan (Storage Efficiency): Format Parquet di layer Silver/Gold jauh lebih kecil dibandingkan CSV di Bronze (Compression Ratio tinggi). Hal ini disebabkan Parquet menggunakan arsitektur columnar dan teknik kompresi cerdas (seperti Snappy/GZIP) per kolom, serta tipe data numerik yang disimpan lebih efisien.")
    print("2. Kecepatan Query (Query Performance): Waktu baca Parquet dengan DuckDB seringkali lebih cepat atau setara, namun keunggulan utama Parquet adalah pada Projection Pushdown (hanya membaca kolom yang diperlukan dalam query analitik nyata), sedangkan CSV mengharuskan parsing seluruh baris teks.")
    print("3. Kesimpulan Arsitektur: Perubahan format dari CSV (Bronze) ke Parquet (Silver/Gold) merupakan Best Practice dalam Data Lakehouse untuk mengoptimalkan biaya storage dan performa komputasi.")

if __name__ == '__main__':
    run_comparison()
