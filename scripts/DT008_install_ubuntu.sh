#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  printf '[DT008] %s\n' "$1" >&2
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

verify_device_user_table() {
  local table

  log "Verifying device_user table"
  table="$(compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -N -e "SHOW TABLES LIKE 'device_user';" 2>/dev/null || true)"
  if [ "${table}" != "device_user" ]; then
    log "Required database table is missing: device_user"
    exit 1
  fi
}

verify_user_parser() {
  log "Verifying USER parser"
  compose exec -T api python -c "from datetime import datetime, UTC; from app.adms import _parse_user_line; user=_parse_user_line('USER PIN=1 Name=raymon Pri=0 Passwd= Card= Grp=1 TZ=0000000100000000 Verify=1 ViceCard= StartDatetime=0 EndDatetime=0', 'DT008_CHECK', datetime.now(UTC), 1); assert user.pin == '1'; assert user.name == 'raymon'; assert user.privilege == '0'; assert user.group_no == '1'; assert user.verify_mode == '1'"
}

main() {
  cd "${PROJECT_DIR}"
  scripts/DT007_install_ubuntu.sh "$@"
  load_env
  verify_device_user_table
  verify_user_parser

  printf '\n'
  printf '========================================\n'
  printf 'USER Parser Ready\n'
  printf 'Application Ready\n'
  printf '========================================\n'
}

main "$@"
