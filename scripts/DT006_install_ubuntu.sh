#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  printf '[DT006] %s\n' "$1" >&2
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

verify_operation_event_table() {
  local table

  log "Verifying operation_event table"
  table="$(compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -N -e "SHOW TABLES LIKE 'operation_event';" 2>/dev/null || true)"
  if [ "${table}" != "operation_event" ]; then
    log "Required database table is missing: operation_event"
    exit 1
  fi
}

verify_operlog_parser() {
  log "Verifying OPERLOG parser"
  compose exec -T api python -c "from datetime import datetime; from app.adms import _parse_operlog_line; event=_parse_operlog_line('OPLOG\t82\t1\t2026-07-10 08:30:00\tserver\tvalue1\tvalue2\tvalue3', 'DT006_CHECK', datetime.now(), 1); assert event.operation_code == '82'; assert event.operation_name == 'Modify Cloud Server Address'; assert event.operator == '1'"
}

main() {
  cd "${PROJECT_DIR}"
  scripts/DT005_install_ubuntu.sh "$@"
  load_env
  verify_operation_event_table
  verify_operlog_parser

  printf '\n'
  printf '========================================\n'
  printf 'OPERLOG Parser Ready\n'
  printf 'Application Ready\n'
  printf '========================================\n'
}

main "$@"
