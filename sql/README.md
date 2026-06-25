# SQL Analytics Queries

Folder ini berisi 6 query analitik yang digunakan dalam proyek Data Lakehouse Indonesia.

Query diasumsikan dijalankan setelah tabel Gold Layer tersedia sebagai tabel DuckDB:

- `dim_province`
- `dim_year`
- `dim_indicator`
- `fact_economics`

Jika dijalankan melalui Python, tabel-tabel tersebut sudah diregistrasikan otomatis oleh `src/05_analytics.py`.
Jika dijalankan di DBeaver/DuckDB manual, load Parquet Gold terlebih dahulu dari MinIO atau file lokal, lalu jalankan query satu per satu.
