#!/usr/bin/env bash
set -euo pipefail

RETENTION_DAYS="${ARTIFACT_RETENTION_DAYS:-30}"
ARTIFACT_DIR="${ARTIFACT_DIR:-/var/lib/docker/volumes/docker_test_artifacts/_data}"
DB_CONNECTION="${DB_CONNECTION:?DB_CONNECTION is required}"

BEFORE_BYTES=$(du -sb "$ARTIFACT_DIR" 2>/dev/null | awk '{print $1}' || echo 0)
DELETED=$(find "$ARTIFACT_DIR" -type f -mtime +"$RETENTION_DAYS" -print -delete | wc -l)
AFTER_BYTES=$(du -sb "$ARTIFACT_DIR" 2>/dev/null | awk '{print $1}' || echo 0)
FREED=$(( BEFORE_BYTES > AFTER_BYTES ? BEFORE_BYTES - AFTER_BYTES : 0 ))

psql "$DB_CONNECTION" -c "INSERT INTO artifact_cleanup_log(files_deleted, space_freed_bytes) VALUES ($DELETED, $FREED);"

DISK_USAGE=$(df "$ARTIFACT_DIR" --output=pcent | tail -1 | tr -dc '0-9')
if [[ "$DISK_USAGE" -gt 80 && -n "${TELEGRAM_BOT_TOKEN:-}" && -n "${TELEGRAM_CHAT_ID:-}" ]]; then
  curl -fsS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d chat_id="$TELEGRAM_CHAT_ID" \
    -d text="⚠️ Test Dashboard Disk Warning: ${DISK_USAGE}% used" >/dev/null
fi
