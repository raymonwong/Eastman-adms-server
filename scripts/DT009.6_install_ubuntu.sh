#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  printf '[DT009.6] %s\n' "$1" >&2
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

verify_device_management_columns() {
  local column_count

  log "Verifying device management columns"
  column_count="$(compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -N -e "SHOW COLUMNS FROM device WHERE Field IN ('location','record_attendance','show_in_console');" 2>/dev/null | wc -l | tr -d ' ')"
  if [ "${column_count}" != "3" ]; then
    log "Required device management columns are missing."
    exit 1
  fi
}

verify_device_management_routes() {
  log "Verifying Device Management page and APIs"
  compose exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/dms', timeout=5).read()"
  compose exec -T api python -c "import json, urllib.request; data=json.loads(urllib.request.urlopen('http://127.0.0.1:8000/api/devices', timeout=5).read()); assert isinstance(data, list)"
}

main() {
  cd "${PROJECT_DIR}"
  scripts/DT009.5_install_ubuntu.sh "$@"
  load_env
  verify_device_management_columns
  verify_device_management_routes

  printf '\n'
  printf '========================================\n'
  printf 'Device Management Ready\n'
  printf 'Device Management URL: http://SERVER_IP:4370/dms\n'
  printf 'Application Ready\n'
  printf '========================================\n'
}

main "$@"
