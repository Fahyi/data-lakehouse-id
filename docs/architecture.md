# Arsitektur Data Lakehouse

## Medallion Architecture Flow

```mermaid
graph TD
    subgraph Data Sources
        API[WikiData SPARQL API]
        BPS[BPS Web API]
    end

    subgraph Bronze Layer [Bronze - Raw Data]
        B_WIKI[(wikidata/provinces)]
        B_PDRB[(bps/pdrb)]
        B_POP[(bps/populasi)]
        
        META_W[Manifest & Checksum]
        META_P[Manifest & Checksum]
    end

    subgraph Silver Layer [Silver - Cleaned Parquet]
        S_WIKI[(wikidata_provinces)]
        S_PDRB[(bps_pdrb)]
        S_POP[(bps_populasi)]
        
        DL1[Delta Log Versioning]
        DL2[Delta Log Versioning]
    end

    subgraph Gold Layer [Gold - Star Schema Parquet]
        G_DIM_P[(dim_province)]
        G_DIM_Y[(dim_year)]
        G_DIM_I[(dim_indicator)]
        G_FACT[(fact_economics)]
    end

    subgraph Analytics
        Q1[Query 1 & 2: Regional]
        Q2[Query 3 & 4: Temporal]
        Q3[Query 5 & 6: Inequality]
    end

    API --"Idempotent Ingestion"--> B_WIKI
    BPS --"Idempotent Ingestion"--> B_PDRB
    BPS --"Idempotent Ingestion"--> B_POP

    B_WIKI -.-> META_W
    B_PDRB -.-> META_P

    B_WIKI --"Clean & Cast Types"--> S_WIKI
    B_PDRB --"Normalize & Clean"--> S_PDRB
    B_POP --"Normalize & Clean"--> S_POP

    S_WIKI -.-> DL1
    S_PDRB -.-> DL2

    S_WIKI --"Build Dimension"--> G_DIM_P
    S_PDRB --"Join & Model"--> G_FACT
    S_POP --"Join & Model"--> G_FACT
    G_DIM_P --"1:N"--> G_FACT
    G_DIM_Y --"1:N"--> G_FACT

    G_FACT --> Q1
    G_FACT --> Q2
    G_FACT --> Q3
```

## Komponen Teknologi
- **Storage**: MinIO (S3-compatible Object Storage) digunakan sebagai tempat penyimpanan file CSV dan Parquet di semua layer.
- **Compute**: DuckDB digunakan untuk transformasi data antar layer dan eksekusi query analitik. DuckDB secara native mendukung baca/tulis format Parquet di MinIO menggunakan ekstensi `httpfs`.
- **Orchestration**: Script Python native dengan proses yang idempotent berdasarkan komputasi *hash* MD5.
- **Data Source**: Ingestion BPS memakai API resmi `webapi.bps.go.id`; file di `data/seed/` hanya snapshot pendukung dan bukan sumber utama pipeline.

## Desain Skema Gold (Star Schema)
Skema *Star* dirancang untuk mempermudah analitik agregasi:
1. `fact_economics`: Berisi metrik PDRB dan Populasi, serta nilai turunan *GDP per capita*.
2. `dim_province`: Dimensi geografis yang diperkaya dengan data eksternal dari WikiData (Koordinat, Luas Wilayah).
3. `dim_year`: Dimensi waktu temporal.
4. `dim_indicator`: Metadata statis indikator ekonomi.

## Catatan Cakupan Data

- `dim_province` Gold Layer memuat 38 provinsi aktif berdasarkan ISO code dari Wikidata.
- BPS PDRB live menghasilkan 174 baris untuk periode 2019–2023.
- BPS populasi live menghasilkan 170 baris; endpoint populasi BPS memiliki nilai kosong untuk 4 provinsi DOB Papua baru pada 2023.
