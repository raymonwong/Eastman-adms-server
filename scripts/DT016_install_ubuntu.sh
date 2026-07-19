#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  echo "[DT016] $*"
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
  bash scripts/DT015_install_ubuntu.sh "$@"

  log "Ensuring alert configuration defaults"
  ensure_env_default "ADMS_ALERT_ENABLED" "true"
  ensure_env_default "ADMS_ALERT_WEBHOOK_URL" ""
  ensure_env_default "ADMS_ALERT_CHECK_INTERVAL_SECONDS" "60"
  ensure_env_default "ADMS_ALERT_COOLDOWN_MINUTES" "30"
  ensure_env_default "ADMS_ALERT_DEVICE_OFFLINE_MINUTES" "5"
  ensure_env_default "ADMS_ALERT_HEARTBEAT_TIMEOUT_MINUTES" "5"
  ensure_env_default "ADMS_ALERT_ATTENDANCE_FAILED_THRESHOLD" "1"
  ensure_env_default "ADMS_ALERT_USER_FAILED_THRESHOLD" "1"
  ensure_env_default "ADMS_ALERT_FINGERPRINT_FAILED_THRESHOLD" "1"
  ensure_env_default "ADMS_ALERT_BACKUP_MAX_AGE_HOURS" "36"

  log "Restarting API with alert settings"
  docker compose up -d --build api

  log "Verifying Alert Settings page"
  docker compose exec -T api python - <<'PY'
import urllib.request

from app.main import app

routes = {route.path for route in app.routes}
assert "/settings/alerts" in routes
assert "/api/settings/alerts" in routes
assert "/api/settings/alerts/test" in routes

alert_page = urllib.request.urlopen("http://127.0.0.1:8000/settings/alerts", timeout=10).read().decode("utf-8")
assert "Alert Settings" in alert_page
assert "Webhook URL" in alert_page

backup_page = urllib.request.urlopen("http://127.0.0.1:8000/settings/backup", timeout=10).read().decode("utf-8")
assert 'id="hostDir"' in backup_page
assert "readonly" in backup_page

alert_data = urllib.request.urlopen("http://127.0.0.1:8000/api/settings/alerts", timeout=10).read().decode("utf-8")
assert "alert_count" in alert_data
PY

  echo "========================================"
  echo "DT016 Alert Settings Ready"
  echo "Console Page: /settings/alerts"
  echo "Backup host directory is read-only in UI and API save flow."
  echo "========================================"
}

main "$@"
