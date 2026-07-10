#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  printf '[DT005] %s\n' "$1" >&2
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

verify_attendance_event_table() {
  local table

  log "Verifying attendance_event table"
  table="$(compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -N -e "SHOW TABLES LIKE 'attendance_event';" 2>/dev/null || true)"
  if [ "${table}" != "attendance_event" ]; then
    log "Required database table is missing: attendance_event"
    exit 1
  fi
}

verify_attlog_parser() {
  log "Verifying ATTLOG parser"
  compose exec -T api python -c "from datetime import datetime; from app.adms import _parse_attlog_line; event=_parse_attlog_line('1001\t2026-07-10 08:30:00\t0\t1\t0\t0\t0', 'DT005_CHECK', datetime.now(), 1); assert event.pin == '1001'; assert event.verify == '1'; assert event.work_code == '0'"
}

main() {
  cd "${PROJECT_DIR}"
  scripts/DT004_install_ubuntu.sh "$@"
  load_env
  verify_attendance_event_table
  verify_attlog_parser

  printf '\n'
  printf '========================================\n'
  printf 'ATTLOG Parser Ready\n'
  printf 'Application Ready\n'
  printf '========================================\n'
}

main "$@"
