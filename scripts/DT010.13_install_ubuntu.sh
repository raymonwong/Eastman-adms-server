#!/usr/bin/env bash
set -euo pipefail

TEST_EMPLOYEE_ID="DT01013_EMPLOYEE"
TEST_PIN="9013"
CONFLICT_EMPLOYEE_ID="DT01013_CONFLICT"

log() {
  printf '[DT010.13] %s\n' "$1" >&2
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
DELETE FROM device_user_sync WHERE employee_id IN ('${TEST_EMPLOYEE_ID}', '${CONFLICT_EMPLOYEE_ID}');
DELETE FROM device_user WHERE employee_id IN ('${TEST_EMPLOYEE_ID}', '${CONFLICT_EMPLOYEE_ID}');
" >/dev/null 2>&1 || true
}

verify_pin_support() {
  log "Verifying Mingdao user PIN support"
  compose exec -T api python - <<PY
import json
import os
import urllib.error
import urllib.request

token = os.environ["MINGDAO_API_TOKEN"]
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

payload = {
    "employee_id": "${TEST_EMPLOYEE_ID}",
    "pin": "${TEST_PIN}",
    "name": "DT010.13 Pin Check",
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
assert response["employee_id"] == "${TEST_EMPLOYEE_ID}"
assert response["pin"] == "${TEST_PIN}"

request = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/users/${TEST_EMPLOYEE_ID}",
    headers={"Authorization": f"Bearer {token}"},
)
user = json.loads(urllib.request.urlopen(request, timeout=5).read())
assert user["employee_id"] == "${TEST_EMPLOYEE_ID}"
assert user["pin"] == "${TEST_PIN}"

conflict_payload = dict(payload)
conflict_payload["employee_id"] = "${CONFLICT_EMPLOYEE_ID}"
conflict_payload["name"] = "DT010.13 Conflict Check"
request = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/users",
    data=json.dumps(conflict_payload).encode(),
    headers=headers,
    method="POST",
)
try:
    urllib.request.urlopen(request, timeout=5)
    raise AssertionError("duplicate PIN was not rejected")
except urllib.error.HTTPError as exc:
    assert exc.code == 409
PY
}

main() {
  cd "$(dirname "$0")/.."
  load_env
  cleanup_test_data
  scripts/DT010.11_install_ubuntu.sh "$@"
  cleanup_test_data
  verify_pin_support
  cleanup_test_data

  printf '==================================\n'
  printf 'DT010.13 Mingdao PIN Support Ready\n'
  printf 'API: POST /api/v1/users\n'
  printf 'employee_id and pin are separated\n'
  printf 'Duplicate PIN returns 409 Conflict\n'
  printf '==================================\n'
}

main "$@"
