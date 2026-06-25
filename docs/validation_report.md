# Validation Report

Tanggal validasi: 24 Juni 2026.

## Infrastruktur

```text
docker compose ps
STATUS: datalakehouse-minio Up, healthy
PORTS: 9000 API, 9001 Console
```

## Pipeline ETL

```text
python3 src/01_ingestion_wikidata.py
Successfully fetched 100 records from WikiData.
No changes detected in WikiData source. Skipping ingestion.

python3 src/02_ingestion_bps.py
Fetched 174 PDRB records.
Fetched 170 Population records.

python3 src/03_silver_transform.py
Saved wikidata_provinces version 7 with 42 records.
Saved bps_pdrb version 7 with 174 records.
Saved bps_populasi version 7 with 170 records.

python3 src/04_gold_transform.py
dim_province: 38 rows
dim_year: 5 rows
dim_indicator: 3 rows
fact_economics: 174 rows
All provinces matched successfully.
```

## Analytics

```text
python3 src/05_analytics.py
Query 1: OK
Query 2: OK
Query 3: OK
Query 4: OK
Query 5: OK
Query 6: OK
```

## SQL Files

```text
01_top_gdp_per_capita.sql: OK (5 rows)
02_avg_gdp_by_island.sql: OK (7 rows)
03_java_yoy_growth.sql: OK (30 rows)
04_population_trend.sql: OK (5 rows)
05_gdp_per_capita_category.sql: OK (2 rows)
06_density_vs_gdp.sql: OK (10 rows)
```

## Bonus Scripts

```text
python3 src/06_bonus_comparison.py
OK — comparison CSV vs Parquet berhasil.

python3 src/07_bonus_explain.py
OK — DuckDB query plan berhasil ditampilkan.
```

## Catatan Data

Endpoint BPS populasi tahun 2023 memiliki nilai kosong untuk empat provinsi DOB Papua baru:

- Papua Barat Daya
- Papua Selatan
- Papua Tengah
- Papua Pegunungan

Hal ini membuat query yang memfilter `population > 0` menghitung 34 provinsi, sedangkan `dim_province` tetap memuat 38 provinsi aktif.
