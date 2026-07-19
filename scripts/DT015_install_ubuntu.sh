#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  echo "[DT015] $*"
}

ensure_env_default() {
  local key="$1"
  local value="$2"
  if ! grep -q "^${key}=" .env 2>/dev/null; then
    echo "${key}=${value}" >> .env
  fi
}

main() {
  cd "${PROJECT_DIR}"

  log "Deploying current project"
  bash scripts/DT014_install_ubuntu.sh "$@"

  log "Ensuring backup configuration defaults"
  ensure_env_default "ADMS_BACKUP_ENABLED" "true"
  ensure_env_default "ADMS_BACKUP_TIME" "03:30"
  ensure_env_default "ADMS_BACKUP_RETENTION_COUNT" "14"
  ensure_env_default "ADMS_BACKUP_HOST_DIR" "/opt/eastman/Eastman-adms-server/backups"
  ensure_env_default "ADMS_BACKUP_CONTAINER_DIR" "/app/backup"

  set -a
  # shellcheck disable=SC1091
  . ".env"
  set +a

  mkdir -p "${ADMS_BACKUP_HOST_DIR:-/opt/eastman/Eastman-adms-server/backups}"
  chmod +x scripts/DT015_backup_create.sh scripts/DT015_backup_cron_install.sh scripts/DT015_backup_restore.sh

  log "Restarting API with backup settings"
  docker compose up -d --build api

  log "Verifying Backup Settings page"
  docker compose exec -T api python - <<'PY'
import urllib.request

from app.main import app

routes = {route.path for route in app.routes}
assert "/settings/backup" in routes
assert "/api/settings/backup" in routes
assert "/settings/backup/download/{filename}" in routes

page = urllib.request.urlopen("http://127.0.0.1:8000/settings/backup", timeout=10).read().decode("utf-8")
assert "Backup Settings" in page
assert "Latest Backup Records" in page
PY

  echo "========================================"
  echo "DT015 Backup Settings Ready"
  echo "Console Page: /settings/backup"
  echo "Manual Backup: bash scripts/DT015_backup_create.sh"
  echo "Install Schedule: bash scripts/DT015_backup_cron_install.sh"
  echo "Restore Guide: docs/Backup_and_Restore.md"
  echo "========================================"
}

main "$@"
