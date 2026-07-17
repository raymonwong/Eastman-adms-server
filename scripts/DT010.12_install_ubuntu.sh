#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_EMPLOYEE_ID="DT01012_RECORD"
TEST_PIN="9012"
TEST_RECORD_ID="659823456789"

log() {
  echo "[DT010.12] $*"
}

compose() {
  docker compose "$@"
}

load_env() {
  if [ -f "${PROJECT_DIR}/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "${PROJECT_DIR}/.env"
    set +a
  fi
}

cleanup_test_data() {
  compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -e "
DELETE FROM device_user_sync WHERE employee_id = '${TEST_EMPLOYEE_ID}';
DELETE FROM device_user WHERE employee_id = '${TEST_EMPLOYEE_ID}';
" >/dev/null
}

verify_employee_record_id() {
  log "Verifying employee_record_id database column"
  compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -N -e "
SHOW COLUMNS FROM device_user LIKE 'employee_record_id';
" | grep -q "employee_record_id"

  log "Verifying employee_record_id validation and read APIs"
  compose exec -T api python - <<'PY'
import json
import os
import urllib.request

import app.main  # noqa: F401
from pydantic import ValidationError

from app.database import SessionLocal
from app.mingdao_users import UserSyncRequest
from app.models import DeviceUser

employee_id = "DT01012_RECORD"
pin = "9012"
record_id = "659823456789"

try:
    UserSyncRequest.model_validate(
        {
            "employee_id": employee_id,
            "pin": pin,
            "name": "DT010.12 Record ID Check",
            "department": "Install Check",
            "privilege": 0,
            "enabled": True,
        }
    )
    raise AssertionError("employee_record_id validation did not fail")
except ValidationError:
    pass

payload = UserSyncRequest.model_validate(
    {
        "employee_record_id": record_id,
        "employee_id": employee_id,
        "pin": pin,
        "name": "DT010.12 Record ID Check",
        "department": "Install Check",
        "privilege": 0,
        "enabled": True,
    }
)
assert payload.employee_record_id == record_id

with SessionLocal() as session:
    user = session.query(DeviceUser).filter(DeviceUser.employee_id == employee_id).one_or_none()
    if user is None:
        user = DeviceUser(employee_id=employee_id)
        session.add(user)
    user.employee_record_id = record_id
    user.pin = pin
    user.name = "DT010.12 Record ID Check"
    user.department = "Install Check"
    user.privilege = "0"
    user.enabled = True
    session.commit()

token = os.environ.get("MINGDAO_API_TOKEN", "").strip()
default_tokens = {"", "changeme", "changeme-mingdao-token", "password", "123456", "please_change_me"}
if token.lower() not in default_tokens:
    request = urllib.request.Request(
        f"http://127.0.0.1:8000/api/v1/users/{employee_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    api_user = json.loads(urllib.request.urlopen(request, timeout=10).read().decode("utf-8"))
    assert api_user["employee_record_id"] == record_id

console_data = json.loads(urllib.request.urlopen("http://127.0.0.1:8000/api/adms-users", timeout=10).read().decode("utf-8"))
matches = [
    user
    for group in console_data["groups"]
    for user in group["users"]
    if user["employee_id"] == employee_id
]
assert matches, "test user not found in ADMS Users Console API"
assert matches[0]["employee_record_id"] == record_id
PY
}

main() {
  cd "${PROJECT_DIR}"
  load_env

  log "Cleaning install verification data"
  cleanup_test_data || true

  log "Deploying current project"
  bash scripts/DT011.1_install_ubuntu.sh "$@"
  load_env

  cleanup_test_data || true
  verify_employee_record_id
  cleanup_test_data || true

  echo "========================================"
  echo "DT010.12 Employee Record ID Ready"
  echo "Column: device_user.employee_record_id"
  echo "API: POST /api/v1/users"
  echo "Console: /users"
  echo "========================================"
}

main "$@"
