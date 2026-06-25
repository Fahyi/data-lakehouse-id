#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "== Data Lakehouse Indonesia Pipeline =="

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker tidak ditemukan. Install dan jalankan Docker Desktop dulu."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 tidak ditemukan. Install Python 3.9+ dulu."
  exit 1
fi

if [ ! -f ".env" ]; then
  echo "File .env belum ada. Membuat dari .env.example ..."
  cp .env.example .env
fi

echo
echo "1/7 Menjalankan MinIO via Docker Compose..."
docker compose up -d

echo
echo "2/7 Install/cek Python dependencies..."
python3 -m pip install -r requirements.txt

echo
echo "3/7 Bronze ingestion - Wikidata..."
python3 src/01_ingestion_wikidata.py

echo
echo "4/7 Bronze ingestion - BPS..."
python3 src/02_ingestion_bps.py

echo
echo "5/7 Silver transformation..."
python3 src/03_silver_transform.py

echo
echo "6/7 Gold transformation..."
python3 src/04_gold_transform.py

echo
echo "7/7 Analytics queries..."
python3 src/05_analytics.py

echo
echo "Pipeline selesai."
echo "MinIO Console: http://localhost:9001"
echo "Login default: minioadmin / minioadmin"
