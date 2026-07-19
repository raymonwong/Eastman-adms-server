#!/usr/bin/env bash
set -euo pipefail

TEST_DEVICE_SN="DT0111_DEVICE"
TEST_EMPLOYEE_ID="DT0111_EMPLOYEE"
TEST_PIN="9111"

log() {
  printf '[DT011.1] %s\n' "$1" >&2
}

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  else
    docker-compose "$@"
  fi
}

load_env() {
  if [ ! -f ".env" ]; then
    log ".env not found. Run the previous install script first."
    exit 1
  fi

  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
}

cleanup_test_data() {
  compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -e "
SET FOREIGN_KEY_CHECKS=0;
DELETE FROM device_user_fingerprint_sync WHERE device_sn='${TEST_DEVICE_SN}' OR pin='${TEST_PIN}';
DELETE FROM device_user_fingerprint WHERE device_sn='${TEST_DEVICE_SN}' OR source_device_sn='${TEST_DEVICE_SN}' OR pin='${TEST_PIN}';
DELETE FROM device_user_sync WHERE employee_id='${TEST_EMPLOYEE_ID}' OR device_sn='${TEST_DEVICE_SN}';
DELETE FROM device_user WHERE employee_id='${TEST_EMPLOYEE_ID}' OR pin='${TEST_PIN}';
DELETE FROM device WHERE device_sn='${TEST_DEVICE_SN}';
SET FOREIGN_KEY_CHECKS=1;
" >/dev/null 2>&1 || true
}

verify_record_attendance_sync_scope() {
  log "Verifying record_attendance controls user sync scope"
  compose exec -T api python - <<PY
import json
import urllib.request

import app.main  # Initializes the database engine and binds SessionLocal.
from app.database import SessionLocal
from app.models import Device, DeviceUser, DeviceUserSync

with SessionLocal() as session:
    session.add(
        Device(
            device_sn="${TEST_DEVICE_SN}",
            device_name="DT011.1 Test Device",
            status="online",
            record_attendance=False,
            show_in_console=False,
        )
    )
    session.add(
        DeviceUser(
            employee_id="${TEST_EMPLOYEE_ID}",
            pin="${TEST_PIN}",
            name="DT011.1 User",
            department="IT",
            privilege="0",
            enabled=True,
        )
    )
    session.commit()

with SessionLocal() as session:
    off_sync = (
        session.query(DeviceUserSync)
        .filter(DeviceUserSync.employee_id == "${TEST_EMPLOYEE_ID}", DeviceUserSync.device_sn == "${TEST_DEVICE_SN}")
        .one_or_none()
    )
    assert off_sync is None, "record_attendance OFF device should not receive sync records"

put_payload = {
    "device_name": "DT011.1 Test Device",
    "location": "Install Test",
    "record_attendance": True,
    "show_in_console": True,
}
put_request = urllib.request.Request(
    "http://127.0.0.1:8000/api/device/${TEST_DEVICE_SN}",
    data=json.dumps(put_payload).encode(),
    headers={"Content-Type": "application/json"},
    method="PUT",
)
urllib.request.urlopen(put_request, timeout=5).read()

with SessionLocal() as session:
    on_sync = (
        session.query(DeviceUserSync)
        .filter(DeviceUserSync.employee_id == "${TEST_EMPLOYEE_ID}", DeviceUserSync.device_sn == "${TEST_DEVICE_SN}")
        .one_or_none()
    )
    assert on_sync is not None, "record_attendance ON should create missing sync records"
    assert on_sync.sync_status == "PENDING", on_sync.sync_status

command = urllib.request.urlopen("http://127.0.0.1:8000/iclock/getrequest?SN=${TEST_DEVICE_SN}", timeout=5).read().decode()
assert command.startswith("C:"), command
assert "DATA UPDATE USERINFO" in command, command
assert "PIN=${TEST_PIN}" in command, command
PY
}

main() {
  cd "$(dirname "$0")/.."
  load_env
  cleanup_test_data
  scripts/DT011_install_ubuntu.sh "$@"
  cleanup_test_data
  verify_record_attendance_sync_scope
  cleanup_test_data

  printf '==================================\n'
  printf 'DT011.1 User Sync Scope Ready\n'
  printf 'record_attendance OFF skipped ... OK\n'
  printf 'record_attendance ON rebuild .... OK\n'
  printf 'GETREQUEST command delivery ..... OK\n'
  printf '==================================\n'
}

main "$@"
