# Cara Menjalankan Project di Laptop Baru

Panduan ini untuk teman/anggota kelompok yang menjalankan project dari nol.

## 1. Prasyarat

Install:

- Python 3.9 atau lebih baru
- Docker Desktop
- Git, jika mengambil project dari GitHub

Pastikan Docker Desktop sedang berjalan sebelum menjalankan pipeline.

## 2. Ambil Project

Jika dari GitHub:

```bash
git clone <URL_REPOSITORY>
cd data-lakehouse-id
```

Jika dari ZIP:

```bash
unzip data-lakehouse-id.zip
cd data-lakehouse-id
```

## 3. Cek Environment

```bash
bash scripts/check_environment.sh
```

Jika Docker daemon belum OK, buka Docker Desktop dulu lalu ulangi command di atas.

## 4. Jalankan Pipeline Sekali Jalan

```bash
bash scripts/run_pipeline.sh
```

Script ini akan:

1. Membuat `.env` dari `.env.example` jika belum ada.
2. Menjalankan MinIO dengan Docker Compose.
3. Menginstall dependencies Python.
4. Menjalankan ingestion Wikidata.
5. Menjalankan ingestion BPS.
6. Menjalankan Silver dan Gold transformation.
7. Menjalankan 6 query analytics.

## 5. Cara Manual

Jika ingin menjalankan step-by-step:

```bash
cp .env.example .env
docker compose up -d
python3 -m pip install -r requirements.txt

python3 src/01_ingestion_wikidata.py
python3 src/02_ingestion_bps.py
python3 src/03_silver_transform.py
python3 src/04_gold_transform.py
python3 src/05_analytics.py
```

## 6. Cek MinIO

Buka:

```text
http://localhost:9001
```

Login default:

```text
username: minioadmin
password: minioadmin
```

Bucket default:

```text
datalakehouse
```

Isi yang diharapkan:

- `bronze/`
- `silver/`
- `gold/`

## 7. Output yang Diharapkan

Output utama:

```text
Wikidata fetched 100 records
BPS PDRB fetched 174 records
BPS Population fetched 170 records
dim_province: 38 rows
dim_year: 5 rows
dim_indicator: 3 rows
fact_economics: 174 rows
6 query analytics berhasil jalan
```

Catatan: jika ingestion menyebut `data unchanged`, itu normal. Artinya checksum mendeteksi data terbaru sama dengan data sebelumnya.

## 8. Troubleshooting

### Docker error: cannot connect to Docker daemon

Solusi:

- Buka Docker Desktop.
- Tunggu sampai status Docker running.
- Ulangi `bash scripts/run_pipeline.sh`.

### Port 9000 atau 9001 sudah dipakai

Solusi cepat:

- Matikan service lain yang memakai port tersebut, atau
- Ubah port di `docker-compose.yml` dan sesuaikan `MINIO_ENDPOINT` di `.env`.

### BPS/Wikidata gagal fetch

Solusi:

- Pastikan internet aktif.
- Matikan VPN/firewall jika menghalangi akses API.
- Jalankan ulang script ingestion.

### Python package error

Solusi:

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

## 9. File yang Jangan Dibagikan

Jangan commit atau upload:

- `.env`
- `.DS_Store`
- `__pycache__/`
- file log/cache lokal

File `.gitignore` sudah disiapkan untuk membantu menghindari file-file tersebut.
