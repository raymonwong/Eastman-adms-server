#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  printf '[DT012.1] %s\n' "$1" >&2
}

compose() {
  docker compose --env-file "${PROJECT_DIR}/.env" -f "${PROJECT_DIR}/docker-compose.yml" "$@"
}

load_env() {
  if [ ! -f "${PROJECT_DIR}/.env" ]; then
    log ".env not found. Run the previous install script first."
    exit 1
  fi

  set -a
  # shellcheck disable=SC1091
  . "${PROJECT_DIR}/.env"
  set +a
}

verify_fingerprint_table() {
  log "Verifying fingerprint upload table"
  local column_count
  column_count="$(compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -N -e "SHOW COLUMNS FROM device_user_fingerprint WHERE Field IN ('device_sn','pin','finger_id','template_size','valid','template_data','template_hash','source_device_sn','raw_request_id');" 2>/dev/null | wc -l | tr -d ' ')"
  if [ "${column_count}" != "9" ]; then
    log "Required device_user_fingerprint columns are missing."
    exit 1
  fi
}

verify_fp_parser() {
  log "Verifying FP parser"
  compose exec -T api python - <<'PY'
from datetime import datetime, UTC

from app.adms import _parse_fp_line

line = "FP PIN=23\tFID=6\tSize=1424\tValid=1\tTMP=TEST_TEMPLATE_DATA"
fingerprint = _parse_fp_line(line, "DT0121_DEVICE", datetime.now(UTC), 1)
assert fingerprint.device_sn == "DT0121_DEVICE"
assert fingerprint.source_device_sn == "DT0121_DEVICE"
assert fingerprint.pin == "23"
assert fingerprint.finger_id == "6"
assert fingerprint.template_size == 1424
assert fingerprint.valid == "1"
assert fingerprint.template_data == "TEST_TEMPLATE_DATA"
assert len(fingerprint.template_hash) == 64
PY
}

main() {
  cd "${PROJECT_DIR}"
  load_env
  scripts/DT010.13_install_ubuntu.sh "$@"
  verify_fingerprint_table
  verify_fp_parser

  printf '\n'
  printf '========================================\n'
  printf 'DT012.1 FP Upload Parser Ready\n'
  printf 'Table: device_user_fingerprint\n'
  printf 'Parser: OPERLOG body record type FP\n'
  printf 'Distribution: not implemented in DT012.1\n'
  printf '========================================\n'
}

main "$@"
