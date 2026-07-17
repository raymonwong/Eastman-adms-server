#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  echo "[DT014] $*"
}

compose() {
  docker compose "$@"
}

main() {
  cd "${PROJECT_DIR}"

  log "Deploying current project"
  bash scripts/DT013.1_install_ubuntu.sh "$@"

  log "Verifying attendance Mingdao sync database objects"
  table="$(compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -N -e "SHOW TABLES LIKE 'attendance_mingdao_sync';" 2>/dev/null || true)"
  if [ "${table}" != "attendance_mingdao_sync" ]; then
    log "Required database table is missing: attendance_mingdao_sync"
    exit 1
  fi

  constraint_count="$(compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -N -e "SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA='${MYSQL_DATABASE}' AND TABLE_NAME='attendance_mingdao_sync' AND CONSTRAINT_NAME IN ('uq_attendance_mingdao_sync_event','ck_attendance_mingdao_sync_status','fk_attendance_mingdao_sync_event');" 2>/dev/null | tr -d ' ')"
  if [ "${constraint_count}" -lt "3" ]; then
    log "Required attendance_mingdao_sync constraints are missing."
    exit 1
  fi

  log "Verifying attendance sync routes and duplicate-prevention helpers"
  compose exec -T api python - <<'PY'
import urllib.request

import app.main
from app.main import app
from app.mingdao_attendance import _attendance_rows_url, attendance_sync_status_summary

routes = {route.path for route in app.routes}
assert "/api/settings/integration/attendance/sync" in routes
assert _attendance_rows_url("https://api.mingdao.com", "worksheet001") == "https://api.mingdao.com/v3/app/worksheets/worksheet001/rows"

status = attendance_sync_status_summary()
assert {"PENDING", "SYNCING", "SYNCED", "FAILED", "TOTAL"}.issubset(status)

page = urllib.request.urlopen("http://127.0.0.1:8000/settings/attendance-sync", timeout=10).read().decode("utf-8")
assert "Sync Now" in page
assert "attendance_mingdao_sync.attendance_event_id" in page
PY

  echo "========================================"
  echo "DT014 Mingdao Attendance Sync Ready"
  echo "Attendance Sync Page: /settings/attendance-sync"
  echo "Manual upload button: Sync Now"
  echo "Duplicate key: attendance_mingdao_sync.attendance_event_id"
  echo "No automatic attendance upload was executed by this installer"
  echo "========================================"
}

main "$@"
