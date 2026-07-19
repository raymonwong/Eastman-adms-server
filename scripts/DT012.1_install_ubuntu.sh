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

  log "Verifying fingerprint distribution queue table"
  local sync_column_count
  sync_column_count="$(compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -N -e "SHOW COLUMNS FROM device_user_fingerprint_sync WHERE Field IN ('fingerprint_id','device_sn','pin','finger_id','template_hash','sync_status','last_sync_time','retry_count','last_error');" 2>/dev/null | wc -l | tr -d ' ')"
  if [ "${sync_column_count}" != "9" ]; then
    log "Required device_user_fingerprint_sync columns are missing."
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

verify_heartbeat_retention() {
  log "Verifying heartbeat raw_request retention"
  local index_count
  index_count="$(compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -N -e "SHOW INDEX FROM raw_request WHERE Key_name='ix_raw_request_path_received_at';" 2>/dev/null | wc -l | tr -d ' ')"
  if [ "${index_count}" = "0" ]; then
    log "Required raw_request heartbeat retention index is missing."
    exit 1
  fi

  compose exec -T api python - <<'PY'
from datetime import UTC, datetime, timedelta

from app.adms import HEARTBEAT_RAW_REQUEST_RETENTION_DAYS, _cleanup_old_heartbeat_raw_requests
from app.database import SessionLocal
from app.models import RawRequest

device_sn = "DT0121_HEARTBEAT_RETENTION"
old_time = datetime.now(UTC) - timedelta(days=HEARTBEAT_RAW_REQUEST_RETENTION_DAYS + 1)

with SessionLocal() as session:
    session.query(RawRequest).filter(RawRequest.device_sn == device_sn).delete(synchronize_session=False)
    session.add(
        RawRequest(
            device_sn=device_sn,
            request_method="GET",
            request_url="http://127.0.0.1:8000/iclock/getrequest?SN=DT0121_HEARTBEAT_RETENTION",
            request_path="/iclock/getrequest",
            query_string=f"SN={device_sn}",
            query_params="[]",
            headers="[]",
            body="",
            client_ip="127.0.0.1",
            user_agent="DT012.1 install check",
            content_type=None,
            response_body="OK",
            response_status_code=200,
            request_size=0,
            response_size=2,
            parsed=False,
            request_hash="dt0121_heartbeat_retention_check",
            received_at=old_time,
        )
    )
    session.commit()

deleted_count = _cleanup_old_heartbeat_raw_requests(datetime.now(UTC))

with SessionLocal() as session:
    remaining = session.query(RawRequest).filter(RawRequest.device_sn == device_sn).count()

assert deleted_count >= 1
assert remaining == 0
PY
}

main() {
  cd "${PROJECT_DIR}"
  load_env
  scripts/DT010.13_install_ubuntu.sh "$@"
  verify_fingerprint_table
  verify_fp_parser
  verify_heartbeat_retention

  printf '\n'
  printf '========================================\n'
  printf 'DT012.1 FP Upload Parser Ready\n'
  printf 'Table: device_user_fingerprint\n'
  printf 'Queue: device_user_fingerprint_sync\n'
  printf 'Parser: OPERLOG body record type FP\n'
  printf 'Heartbeat raw_request retention: 3 days\n'
  printf 'Distribution: queued on FP change and delivered by GETREQUEST\n'
  printf '========================================\n'
}

main "$@"
