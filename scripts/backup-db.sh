#!/usr/bin/env bash
set -euo pipefail

DB_CONNECTION="${DB_CONNECTION:?DB_CONNECTION is required}"
BACKUP_DIR="${BACKUP_DIR:-/backups/testdashboard}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
mkdir -p "$BACKUP_DIR"

FILE="$BACKUP_DIR/testdashboard-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"
pg_dump "$DB_CONNECTION" | gzip > "$FILE"
find "$BACKUP_DIR" -type f -name 'testdashboard-*.sql.gz' -mtime +"$RETENTION_DAYS" -delete
printf 'Created backup: %s\n' "$FILE"
