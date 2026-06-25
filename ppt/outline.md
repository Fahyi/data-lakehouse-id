# Data Lakehouse Indonesia — Final Presentation Outline

## Slide 1 — Cover

- Data Lakehouse Platform
- Indonesia Demographics & Economy Analysis
- Anggota:
  - Fahyi Nashaqi — 5026241171
  - Gelar Ridho Ramadhan — 5026241045

## Slide 2 — Pendahuluan

- Latar belakang: kebutuhan integrasi data provinsi Indonesia.
- Problem statement: data BPS dan Wikidata tersebar.
- Tujuan: membangun lakehouse MinIO + DuckDB dengan Medallion Architecture.

## Slide 3 — Sumber Data Asli

- Wikidata SPARQL API.
- BPS Web API.
- Screenshot sumber data asli.

## Slide 4 — Data Dictionary dan Volume

- Variabel penting dari Wikidata, BPS PDRB, BPS populasi, Gold Fact.
- Volume hasil pipeline: 38 provinsi aktif, 5 tahun, 174 PDRB rows, 170 populasi rows.
- Catatan missing population untuk 4 DOB Papua baru di endpoint BPS.

## Slide 5 — Arsitektur Bucket MinIO

- Bronze, Silver, Gold.
- Prefix dan isi utama tiap layer.
- Teknologi: MinIO, DuckDB, Docker, Python.

## Slide 6 — Idempotency, Versioning, Auditability

- Checksum MD5 untuk idempotency.
- Delta Log untuk versioning.
- Manifest metadata untuk audit.

## Slide 7 — ERD Gold Layer

- `dim_province`
- `dim_year`
- `dim_indicator`
- `fact_economics`

## Slide 8 — Daftar 6 Query Analitik

- Query 1–3: Fahyi.
- Query 4–6: Gelar.
- Tujuan tiap query.

## Slide 9 — Bukti Keberhasilan ETL

- Ringkasan terminal ingestion Wikidata.
- Ringkasan terminal ingestion BPS.
- Ringkasan Silver dan Gold transformation.

## Slide 10 — Isi Bucket MinIO

- Bronze object/prefix.
- Silver object/prefix.
- Gold object/prefix.

## Slide 11 — Ringkasan Hasil Query

- Top GDP/PDRB per capita.
- Perbandingan regional.
- Kategori ketimpangan.
- Visual chart ringkas.

## Slide 12 — Pembagian Tugas dan Alur Video

- Kontribusi Fahyi.
- Kontribusi Gelar.
- Timeline video demo 10–20 menit.
