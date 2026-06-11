#!/bin/bash

set -e

echo "[$(date -Iseconds)] Verificando migrações do banco de dados..."
alembic upgrade head
echo "[$(date -Iseconds)] Migrações aplicadas."

echo "[$(date -Iseconds)] Iniciando Uvicorn (workers=1 — APScheduler em processo)..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level info