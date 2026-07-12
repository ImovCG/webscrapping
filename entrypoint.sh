#!/bin/sh
set -e

INTERVAL="${SCRAPE_INTERVAL_SECONDS:-604800}"

while true; do
    echo "[entrypoint] iniciando pipeline de coleta..."
    python pipeline.py || echo "[entrypoint] pipeline terminou com erro, tentando novamente no proximo ciclo"
    echo "[entrypoint] proxima coleta em ${INTERVAL}s"
    sleep "$INTERVAL"
done
