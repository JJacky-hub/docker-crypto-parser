#!/bin/bash

# Настройки
BACKUP_DIR="/root/docker-crypto-parser/backups"
CONTAINER_NAME="crypto_postgres"
DB_USER="postgres_user"
DB_NAME="crypto_db"

# Текущая дата для имени файла
DATE=$(date +%Y-%m-%d_%H-%M-%S)
FILE_NAME="${BACKUP_DIR}/db_backup_${DATE}.sql.gz"

# 1. Создаем дамп и сжимаем его на лету
docker exec -t ${CONTAINER_NAME} pg_dump -U ${DB_USER} ${DB_NAME} | gzip > "${FILE_NAME}"

# 2. Проверяем, создался ли файл
if [ -f "${FILE_NAME}" ]; then
    echo "[$(date)] Бэкап успешно создан: ${FILE_NAME}"
else
    echo "[$(date)] Ошибка при создании бэкапа!"
fi

# 3. Удаляем бэкапы старше 7 дней
find "${BACKUP_DIR}" -type f -name "db_backup_*.sql.gz" -mtime +7 -delete
