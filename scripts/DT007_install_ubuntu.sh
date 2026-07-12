#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  printf '[DT007] %s\n' "$1" >&2
}

compose() {
  docker compose --env-file "${PROJECT_DIR}/.env" -f "${PROJECT_DIR}/docker-compose.yml" "$@"
}

load_env() {
  set -a
  # shellcheck disable=SC1091
  . "${PROJECT_DIR}/.env"
  set +a
}

verify_device_sync_state_table() {
  local table

  log "Verifying device_sync_state table"
  table="$(compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -N -e "SHOW TABLES LIKE 'device_sync_state';" 2>/dev/null || true)"
  if [ "${table}" != "device_sync_state" ]; then
    log "Required database table is missing: device_sync_state"
    exit 1
  fi
}

verify_sync_state_update() {
  log "Verifying sync state updater"
  compose exec -T api python -c "import app.main; from datetime import datetime, UTC; from app.adms import _update_device_sync_state; _update_device_sync_state({'device_sn':'DT007_CHECK','received_at':datetime.now(UTC),'raw_request_id':None}, 'ATTLOG', '9999')"
  compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -e "DELETE FROM device_sync_state WHERE device_sn = 'DT007_CHECK';" >/dev/null 2>&1
}

main() {
  cd "${PROJECT_DIR}"
  scripts/DT006_install_ubuntu.sh "$@"
  load_env
  verify_device_sync_state_table
  verify_sync_state_update

  printf '\n'
  printf '========================================\n'
  printf 'Device Sync State Ready\n'
  printf 'Application Ready\n'
  printf '========================================\n'
}

main "$@"
