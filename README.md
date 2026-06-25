# 🇮🇩 Data Lakehouse Platform — Indonesia Demographics & Economy

Final Project Data Engineering: membangun platform **Data Lakehouse** untuk analisis ekonomi dan demografi provinsi Indonesia menggunakan **MinIO** sebagai object storage dan **DuckDB** sebagai compute/query engine.

## Anggota Kelompok

1. Fahyi Nashaqi — 5026241171
2. Gelar Ridho Ramadhan — 5026241045

## Ringkasan Project

Project ini mengintegrasikan data dari:

- **Wikidata SPARQL API** untuk metadata provinsi Indonesia: nama provinsi, kode ISO, ibu kota, luas wilayah, koordinat, dan metadata referensi.
- **Badan Pusat Statistik (BPS) API** untuk data ekonomi-demografi provinsi 2019–2023:
  - PDRB atas dasar harga berlaku.
  - PDRB atas dasar harga konstan.
  - Jumlah penduduk.

Data diproses menggunakan **Medallion Architecture**:

- **Bronze Layer**: data mentah CSV hasil ingestion API + metadata audit.
- **Silver Layer**: data bersih dan terstandardisasi dalam format Parquet + Delta Log versioning.
- **Gold Layer**: star schema analytics-ready untuk query analitik.

## Struktur Repository

```text
.
├── config/                 # Konfigurasi MinIO, DuckDB, environment
├── data/seed/              # Snapshot/seed data BPS
├── docs/                   # Dokumentasi arsitektur, checklist, script video
├── ppt/                    # File presentasi proyek
├── sql/                    # 6 query analitik dalam format .sql
├── src/                    # Python pipeline scripts
│   ├── 01_ingestion_wikidata.py
│   ├── 02_ingestion_bps.py
│   ├── 03_silver_transform.py
│   ├── 04_gold_transform.py
│   ├── 05_analytics.py
│   ├── 06_bonus_comparison.py
│   ├── 07_bonus_explain.py
│   └── utils/
├── docker-compose.yml
└── requirements.txt
```

## Cara Menjalankan

### Cara cepat di laptop baru

```bash
bash scripts/run_pipeline.sh
```

Panduan detail untuk laptop teman/anggota kelompok tersedia di [`docs/run_on_new_laptop.md`](docs/run_on_new_laptop.md).

### 1. Jalankan MinIO

```bash
docker compose up -d
```

MinIO berjalan di:

- API: `http://localhost:9000`
- Console: `http://localhost:9001`
- Username/password default: `minioadmin` / `minioadmin`

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Jalankan Pipeline ETL

```bash
# Bronze ingestion
python3 src/01_ingestion_wikidata.py
python3 src/02_ingestion_bps.py

# Silver & Gold transformation
python3 src/03_silver_transform.py
python3 src/04_gold_transform.py

# Analytics queries
python3 src/05_analytics.py
```

### 4. Jalankan Bonus

```bash
python3 src/06_bonus_comparison.py
python3 src/07_bonus_explain.py
```

## Gold Layer Schema

Gold Layer menggunakan star schema:

- `dim_province`: metadata provinsi dari Wikidata.
- `dim_year`: dimensi tahun 2019–2023.
- `dim_indicator`: metadata indikator ekonomi-demografi.
- `fact_economics`: gabungan PDRB, populasi, dan GDP/PDRB per kapita.

## Query Analitik

File SQL tersedia di folder `sql/`:

1. Top 5 provinsi berdasarkan GDP/PDRB per kapita.
2. Rata-rata GDP/PDRB berdasarkan kelompok pulau.
3. Pertumbuhan PDRB year-over-year provinsi Jawa.
4. Tren populasi nasional dan rata-rata GDP/PDRB per kapita.
5. Kategori provinsi di atas/bawah rata-rata GDP/PDRB per kapita nasional.
6. Kepadatan penduduk vs GDP/PDRB per kapita.

Query yang sama juga dijalankan otomatis oleh `src/05_analytics.py`.

## Fitur Data Engineering

- **Idempotency**: ingestion memakai checksum MD5 agar data yang sama tidak diupload ulang.
- **Custom Metadata**: Bronze Layer menyimpan ingestion timestamp, source name, operator ID, dan manifest JSON.
- **Versioning**: Silver Layer menggunakan Delta Log sederhana dan backup versi Parquet sebelumnya.
- **Columnar Storage**: Silver/Gold memakai Parquet untuk efisiensi storage dan query.
- **DuckDB Analytics**: query analitik dijalankan dengan DuckDB.
- **Bonus Explain Plan**: analisis filter/projection pushdown melalui DuckDB.

## Catatan Data BPS

Pipeline BPS menggunakan endpoint resmi BPS untuk periode 2019–2023. Pada endpoint populasi yang digunakan, data 2023 untuk empat provinsi DOB Papua baru memiliki nilai populasi kosong:

- Papua Barat Daya
- Papua Selatan
- Papua Tengah
- Papua Pegunungan

Karena itu beberapa query yang memfilter `population > 0` menghitung 34 provinsi untuk tren populasi, sementara dimensi provinsi tetap memuat 38 provinsi aktif.

## Presentasi & Video

- PPT final berada di folder `ppt/`.
- Script video demo tersedia di `docs/video_demo_script.md`.
- Checklist submission tersedia di `docs/submission_checklist.md`.
