#!/usr/bin/env bash
set -euo pipefail

echo "== Environment Check =="

echo
echo "Python:"
if command -v python3 >/dev/null 2>&1; then
  python3 --version
else
  echo "NOT FOUND: install Python 3.9+"
fi

echo
echo "pip:"
if python3 -m pip --version >/dev/null 2>&1; then
  python3 -m pip --version
else
  echo "NOT FOUND: pip belum tersedia"
fi

echo
echo "Docker:"
if command -v docker >/dev/null 2>&1; then
  docker --version
  if docker info >/dev/null 2>&1; then
    echo "Docker daemon: OK"
  else
    echo "Docker daemon: belum jalan. Buka Docker Desktop dulu."
  fi
else
  echo "NOT FOUND: install Docker Desktop"
fi

echo
echo "Docker Compose:"
if docker compose version >/dev/null 2>&1; then
  docker compose version
else
  echo "NOT FOUND: Docker Compose belum tersedia"
fi

echo
echo "Project files:"
for file in docker-compose.yml requirements.txt .env.example src/01_ingestion_wikidata.py src/02_ingestion_bps.py; do
  if [ -f "$file" ]; then
    echo "OK: $file"
  else
    echo "MISSING: $file"
  fi
done
