#!/usr/bin/env bash
set -euo pipefail

TEST_DEVICE_SN="DT011_DEVICE"
TEST_EMPLOYEE_ID="DT011_EMPLOYEE"
TEST_PIN="9011"

log() {
  printf '[DT011] %s\n' "$1" >&2
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
DELETE FROM device_user_sync WHERE employee_id='${TEST_EMPLOYEE_ID}' OR device_sn='${TEST_DEVICE_SN}';
DELETE FROM device_user WHERE employee_id='${TEST_EMPLOYEE_ID}';
DELETE FROM device WHERE device_sn='${TEST_DEVICE_SN}';
" >/dev/null 2>&1 || true
}

verify_user_sync_engine() {
  log "Verifying user synchronization engine"
  compose exec -T api python - <<PY
import json
import os
import re
import urllib.parse
import urllib.request

import app.main  # Initializes the database engine and binds SessionLocal.
from app.database import SessionLocal
from app.models import Device, DeviceUserSync

token = os.environ["MINGDAO_API_TOKEN"]
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

with SessionLocal() as session:
    session.add(Device(device_sn="${TEST_DEVICE_SN}", device_name="DT011 Test Device", status="online"))
    session.commit()

payload = {
    "employee_id": "${TEST_EMPLOYEE_ID}",
    "pin": "${TEST_PIN}",
    "name": "DT011 User",
    "department": "IT",
    "card_no": "",
    "privilege": 0,
    "enabled": True,
}
request = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/users",
    data=json.dumps(payload).encode(),
    headers=headers,
    method="POST",
)
response = json.loads(urllib.request.urlopen(request, timeout=5).read())
assert response["success"] is True
assert response["changed"] is True
assert response["sync_records"] >= 1

getrequest_url = "http://127.0.0.1:8000/iclock/getrequest?" + urllib.parse.urlencode({"SN": "${TEST_DEVICE_SN}"})
command = urllib.request.urlopen(getrequest_url, timeout=5).read().decode()
assert command.startswith("C:"), command
assert "DATA UPDATE USERINFO" in command, command
assert "PIN=${TEST_PIN}" in command, command
assert "Name=DT011 User" in command, command
command_id = re.match(r"C:(\\d+):", command).group(1)

ack_body = f"ID={command_id}&Return=0".encode()
ack_request = urllib.request.Request(
    "http://127.0.0.1:8000/iclock/devicecmd?SN=${TEST_DEVICE_SN}",
    data=ack_body,
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    method="POST",
)
ack = urllib.request.urlopen(ack_request, timeout=5).read().decode()
assert ack == "OK"

with SessionLocal() as session:
    sync_record = (
        session.query(DeviceUserSync)
        .filter(DeviceUserSync.employee_id == "${TEST_EMPLOYEE_ID}", DeviceUserSync.device_sn == "${TEST_DEVICE_SN}")
        .one_or_none()
    )
    assert sync_record is not None, "missing sync record"
    assert sync_record.sync_status == "SYNCED", sync_record.sync_status
    assert int(sync_record.retry_count) == 0, sync_record.retry_count

data = json.loads(urllib.request.urlopen("http://127.0.0.1:8000/api/adms-users", timeout=5).read())
target = [item for item in data if item.get("employee_id") == "${TEST_EMPLOYEE_ID}"]
assert target, "test user missing from ADMS Users API"
assert target[0]["synced_sync"] >= 1
assert target[0]["sync_details"]
PY
}

main() {
  cd "$(dirname "$0")/.."
  load_env
  cleanup_test_data
  scripts/DT010.14_install_ubuntu.sh "$@"
  cleanup_test_data
  verify_user_sync_engine
  cleanup_test_data

  printf '==================================\n'
  printf 'DT011 User Sync Engine Ready\n'
  printf 'GETREQUEST user command .... OK\n'
  printf 'devicecmd ACK .............. OK\n'
  printf 'device_user_sync ........... OK\n'
  printf '==================================\n'
}

main "$@"
