#!/bin/bash

set -euo pipefail

BACKUP_DIR="/root/docker-crypto-parser/backups"
CONTAINER_NAME="${POSTGRES_CONTAINER_NAME:-crypto_db}"
DB_USER="${POSTGRES_USER:-postgres_user}"
DB_NAME="${POSTGRES_DB:-crypto_db}"

DATE=$(date +%Y-%m-%d_%H-%M-%S)
FILE_NAME="${BACKUP_DIR}/db_backup_${DATE}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Starting PostgreSQL backup..."

docker exec "${CONTAINER_NAME}" \
  pg_dump -U "${DB_USER}" "${DB_NAME}" \
  | gzip > "${FILE_NAME}"

if [ -s "${FILE_NAME}" ]; then
    echo "[$(date)] Backup created: ${FILE_NAME}"
else
    echo "[$(date)] Backup failed!"
    rm -f "${FILE_NAME}"
    exit 1
fi

find "${BACKUP_DIR}" \
  -type f \
  -name "db_backup_*.sql.gz" \
  -mtime +7 \
  -delete

echo "[$(date)] Backup completed successfully."
