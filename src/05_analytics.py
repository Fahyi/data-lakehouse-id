import sys, os
import pandas as pd
from tabulate import tabulate

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config.settings import get_minio_client, get_duckdb_connection, MINIO_BUCKET_NAME, GOLD_PREFIX
from src.utils.minio_client import download_to_dataframe_parquet

def run_analytics():
    print(f"[{pd.Timestamp.now()}] Initializing Analytics queries...")
    
    client = get_minio_client()
    con = get_duckdb_connection()
    
    # 1. Download Gold Parquet and register as DuckDB tables
    print(f"[{pd.Timestamp.now()}] Loading Gold tables into DuckDB...")
    dim_province = download_to_dataframe_parquet(client, MINIO_BUCKET_NAME, f"{GOLD_PREFIX}dim_province.parquet")
    dim_year = download_to_dataframe_parquet(client, MINIO_BUCKET_NAME, f"{GOLD_PREFIX}dim_year.parquet")
    fact_economics = download_to_dataframe_parquet(client, MINIO_BUCKET_NAME, f"{GOLD_PREFIX}fact_economics.parquet")
    
    con.register('dim_province', dim_province)
    con.register('dim_year', dim_year)
    con.register('fact_economics', fact_economics)
    
    queries = [
        {
            "member": "Fahyi",
            "number": 1,
            "title": "Top 5 Provinces by GDP Per Capita (Latest Year)",
            "sql": """
            SELECT 
                dp.province_name,
                dp.province_name_en,
                f.gdp_current_price,
                f.population,
                ROUND(f.gdp_per_capita, 2) AS gdp_per_capita_juta,
                dp.area_km2
            FROM fact_economics f
            JOIN dim_province dp ON f.province_id = dp.province_id
            JOIN dim_year dy ON f.year_id = dy.year_id
            WHERE dy.year = (SELECT MAX(year) FROM dim_year)
              AND f.gdp_per_capita IS NOT NULL
            ORDER BY f.gdp_per_capita DESC
            LIMIT 5
            """,
            "insight": "Provinsi DKI Jakarta memimpin dengan GDP per kapita tertinggi, jauh melampaui provinsi lainnya, yang menunjukkan tingginya konsentrasi ekonomi di wilayah ibukota."
        },
        {
            "member": "Fahyi",
            "number": 2,
            "title": "Average GDP by Island Group (Latest Year)",
            "sql": """
            SELECT
              CASE
                WHEN dp.province_name IN ('Jakarta', 'DKI Jakarta', 'Jawa Barat', 'Jawa Tengah', 'Yogyakarta', 'DI Yogyakarta', 'Jawa Timur', 'Banten') THEN 'Jawa'
                WHEN dp.province_name IN ('Aceh', 'Sumatera Utara', 'Sumatera Barat', 'Riau', 'Jambi', 'Sumatera Selatan', 'Bengkulu', 'Lampung', 'Kepulauan Bangka Belitung', 'Kepulauan Riau') THEN 'Sumatera'
                WHEN dp.province_name LIKE '%Kalimantan%' THEN 'Kalimantan'
                WHEN dp.province_name LIKE '%Sulawesi%' OR dp.province_name = 'Gorontalo' THEN 'Sulawesi'
                WHEN dp.province_name LIKE '%Papua%' THEN 'Papua'
                WHEN dp.province_name IN ('Bali', 'Nusa Tenggara Barat', 'Nusa Tenggara Timur') THEN 'Bali & Nusa Tenggara'
                WHEN dp.province_name IN ('Maluku', 'Maluku Utara') THEN 'Maluku'
                ELSE 'Lainnya'
              END AS island_group,
              COUNT(*) AS province_count,
              ROUND(AVG(f.gdp_current_price), 2) AS avg_gdp_miliar,
              SUM(f.population) AS total_population,
              ROUND(AVG(f.gdp_per_capita), 2) AS avg_gdp_per_capita
            FROM fact_economics f
            JOIN dim_province dp ON f.province_id = dp.province_id
            JOIN dim_year dy ON f.year_id = dy.year_id
            WHERE dy.year = (SELECT MAX(year) FROM dim_year)
            GROUP BY island_group
            ORDER BY avg_gdp_miliar DESC
            """,
            "insight": "Pulau Jawa mendominasi perekonomian nasional dengan rata-rata GDP tertinggi, sementara wilayah timur Indonesia (seperti Maluku dan Papua) masih tertinggal secara signifikan."
        },
        {
            "member": "Fahyi",
            "number": 3,
            "title": "Year-over-Year GDP Growth Rate for Java Provinces",
            "sql": """
            SELECT 
                dp.province_name,
                dy.year,
                f.gdp_current_price,
                LAG(f.gdp_current_price) OVER (PARTITION BY dp.province_name ORDER BY dy.year) AS prev_year_gdp,
                ROUND(((f.gdp_current_price - LAG(f.gdp_current_price) OVER (PARTITION BY dp.province_name ORDER BY dy.year)) 
                  / NULLIF(LAG(f.gdp_current_price) OVER (PARTITION BY dp.province_name ORDER BY dy.year), 0)) * 100, 2) AS growth_rate_pct
            FROM fact_economics f
            JOIN dim_province dp ON f.province_id = dp.province_id
            JOIN dim_year dy ON f.year_id = dy.year_id
            WHERE dp.province_name IN ('Jakarta', 'DKI Jakarta', 'Jawa Barat', 'Jawa Tengah', 'Jawa Timur', 'Banten', 'Yogyakarta', 'DI Yogyakarta')
            ORDER BY dp.province_name, dy.year
            """,
            "insight": "Terdapat fluktuasi pertumbuhan ekonomi (YoY) di provinsi-provinsi Jawa, dengan penurunan tajam pada tahun 2020 akibat pandemi COVID-19, diikuti oleh pemulihan pada tahun-tahun berikutnya."
        },
        {
            "member": "Gelar",
            "number": 4,
            "title": "National Population Trend with Average GDP Per Capita",
            "sql": """
            SELECT 
                dy.year,
                SUM(f.population) AS total_national_population,
                COUNT(DISTINCT f.province_id) AS province_count,
                ROUND(AVG(f.gdp_per_capita), 2) AS avg_gdp_per_capita,
                ROUND(SUM(f.gdp_current_price), 2) AS total_national_gdp
            FROM fact_economics f
            JOIN dim_year dy ON f.year_id = dy.year_id
            WHERE f.population > 0
            GROUP BY dy.year
            ORDER BY dy.year
            """,
            "insight": "Tren populasi nasional terus meningkat secara bertahap setiap tahunnya, beriringan dengan peningkatan rata-rata GDP per kapita nasional (kecuali saat pandemi 2020)."
        },
        {
            "member": "Gelar",
            "number": 5,
            "title": "Provinces Above vs Below National Average GDP Per Capita",
            "sql": """
            WITH national_avg AS (
              SELECT AVG(f.gdp_per_capita) AS avg_gdp_pc
              FROM fact_economics f
              JOIN dim_year dy ON f.year_id = dy.year_id
              WHERE dy.year = (SELECT MAX(year) FROM dim_year)
                AND f.gdp_per_capita IS NOT NULL
            )
            SELECT
              CASE 
                WHEN f.gdp_per_capita >= na.avg_gdp_pc THEN 'Di Atas Rata-rata'
                ELSE 'Di Bawah Rata-rata'
              END AS kategori,
              COUNT(*) AS jumlah_provinsi,
              ROUND(AVG(f.gdp_per_capita), 2) AS avg_gdp_per_capita,
              ROUND(MIN(f.gdp_per_capita), 2) AS min_gdp_per_capita,
              ROUND(MAX(f.gdp_per_capita), 2) AS max_gdp_per_capita,
              SUM(f.population) AS total_populasi
            FROM fact_economics f
            JOIN dim_year dy ON f.year_id = dy.year_id
            CROSS JOIN national_avg na
            WHERE dy.year = (SELECT MAX(year) FROM dim_year)
              AND f.gdp_per_capita IS NOT NULL
            GROUP BY kategori
            """,
            "insight": "Ketimpangan ekonomi cukup jelas terlihat; lebih banyak provinsi yang berada di bawah rata-rata nasional dibandingkan yang di atasnya. Provinsi-provinsi 'Di Atas Rata-rata' (seperti Jakarta dan Kaltim) menarik rata-rata nasional ke atas secara signifikan."
        },
        {
            "member": "Gelar",
            "number": 6,
            "title": "Population Density vs GDP Per Capita by Province",
            "sql": """
            SELECT 
                dp.province_name,
                f.population,
                dp.area_km2,
                ROUND(CAST(f.population AS DOUBLE) / NULLIF(dp.area_km2, 0), 2) AS population_density,
                ROUND(f.gdp_per_capita, 2) AS gdp_per_capita_juta,
                f.gdp_current_price AS total_gdp_miliar
            FROM fact_economics f
            JOIN dim_province dp ON f.province_id = dp.province_id
            JOIN dim_year dy ON f.year_id = dy.year_id
            WHERE dy.year = (SELECT MAX(year) FROM dim_year)
              AND dp.area_km2 > 0
              AND f.population > 0
            ORDER BY population_density DESC
            LIMIT 10
            """,
            "insight": "Terdapat korelasi antara kepadatan penduduk dengan GDP per kapita di provinsi-provinsi besar seperti DKI Jakarta, namun tidak selalu menjamin kesejahteraan ekonomi di provinsi padat penduduk lainnya."
        }
    ]

    for q in queries:
        print(f"\n{'='*100}")
        print(f"{q['member']} - Query {q['number']}: {q['title']}")
        print(f"{'='*100}")
        print("SQL QUERY:")
        print(q['sql'].strip())
        print("-" * 100)
        
        try:
            df_res = con.execute(q['sql']).df()
            if df_res.empty:
                print("No results returned.")
            else:
                print("RESULTS:")
                print(tabulate(df_res, headers='keys', tablefmt='pretty', showindex=False))
                
            print("-" * 100)
            print(f"INSIGHT: {q['insight']}")
            
        except Exception as e:
            print(f"Error executing query: {e}")

if __name__ == '__main__':
    run_analytics()
