#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_EMPLOYEE_ID="DT010_INSTALL_CHECK"
TEST_EMPLOYEE_RECORD_ID="DT010_INSTALL_CHECK_RECORD"
TEST_PIN="9010"

log() {
  printf '[DT010.1] %s\n' "$1" >&2
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

ensure_env_file() {
  if [ ! -f "${PROJECT_DIR}/.env" ]; then
    log ".env does not exist; creating from .env.example"
    cp "${PROJECT_DIR}/.env.example" "${PROJECT_DIR}/.env"
  fi
}

verify_tables() {
  local sync_table
  local column_count
  local sync_constraint_count

  log "Verifying Mingdao user sync database objects"
  sync_table="$(compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -N -e "SHOW TABLES LIKE 'device_user_sync';" 2>/dev/null || true)"
  if [ "${sync_table}" != "device_user_sync" ]; then
    log "Required database table is missing: device_user_sync"
    exit 1
  fi

  column_count="$(compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -N -e "SHOW COLUMNS FROM device_user WHERE Field IN ('employee_id','department','card_no','enabled','last_device_sn','last_device_user_upload_at','last_device_raw_request_id');" 2>/dev/null | wc -l | tr -d ' ')"
  if [ "${column_count}" != "7" ]; then
    log "Required device_user columns are missing."
    exit 1
  fi

  sync_constraint_count="$(compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -N -e "SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA='${MYSQL_DATABASE}' AND TABLE_NAME='device_user_sync' AND CONSTRAINT_NAME IN ('uq_device_user_sync_employee_device','ck_device_user_sync_status','fk_device_user_sync_employee_id','fk_device_user_sync_device_sn');" 2>/dev/null | tr -d ' ')"
  if [ "${sync_constraint_count}" -lt "4" ]; then
    log "Required device_user_sync constraints are missing."
    exit 1
  fi
}

verify_api_token() {
  case "${MINGDAO_API_TOKEN:-}" in
    ""|"changeme"|"changeme-mingdao-token"|"password"|"123456"|"PLEASE_CHANGE_ME"|"please_change_me")
      log "Please modify MINGDAO_API_TOKEN before deployment."
      exit 1
      ;;
  esac
}

verify_user_api() {
  local user_count
  local duplicate_sync_count

  log "Verifying Mingdao user synchronization API"
  compose exec -T api python -c "import json, os, urllib.request; token=os.environ['MINGDAO_API_TOKEN']; payload={'employee_record_id':'${TEST_EMPLOYEE_RECORD_ID}','employee_id':'${TEST_EMPLOYEE_ID}','pin':'${TEST_PIN}','name':' Install Check ','department':' IT ','card_no':'','privilege':0,'enabled':True}; data=json.dumps(payload).encode(); headers={'Content-Type':'application/json','Authorization':'Bearer '+token}; req=urllib.request.Request('http://127.0.0.1:8000/api/v1/users', data=data, headers=headers, method='POST'); res=json.loads(urllib.request.urlopen(req, timeout=5).read()); assert res['success'] is True; assert res['employee_id'] == '${TEST_EMPLOYEE_ID}'; assert res['employee_record_id'] == '${TEST_EMPLOYEE_RECORD_ID}'; assert res['pin'] == '${TEST_PIN}'; assert res['changed'] is True"
  compose exec -T api python -c "import json, os, urllib.request; token=os.environ['MINGDAO_API_TOKEN']; payload={'employee_record_id':'${TEST_EMPLOYEE_RECORD_ID}','employee_id':'${TEST_EMPLOYEE_ID}','pin':'${TEST_PIN}','name':'Install Check','department':'IT','card_no':'','privilege':0,'enabled':True}; data=json.dumps(payload).encode(); headers={'Content-Type':'application/json','X-API-Key':token}; req=urllib.request.Request('http://127.0.0.1:8000/api/v1/users', data=data, headers=headers, method='POST'); res=json.loads(urllib.request.urlopen(req, timeout=5).read()); assert res['success'] is True; assert res['changed'] is False; assert res['sync_records'] == 0"
  compose exec -T api python -c "import json, os, urllib.request; token=os.environ['MINGDAO_API_TOKEN']; req=urllib.request.Request('http://127.0.0.1:8000/api/v1/users/${TEST_EMPLOYEE_ID}', headers={'Authorization':'Bearer '+token}); user=json.loads(urllib.request.urlopen(req, timeout=5).read()); assert user['employee_id'] == '${TEST_EMPLOYEE_ID}'; assert user['employee_record_id'] == '${TEST_EMPLOYEE_RECORD_ID}'; assert user['pin'] == '${TEST_PIN}'; assert user['name'] == 'Install Check'; assert user['department'] == 'IT'"
  compose exec -T api python -c "import json, os, urllib.request; token=os.environ['MINGDAO_API_TOKEN']; payload=[{'employee_record_id':'${TEST_EMPLOYEE_RECORD_ID}','employee_id':'${TEST_EMPLOYEE_ID}','pin':'${TEST_PIN}','name':'Install Check','department':'IT','card_no':'','privilege':0,'enabled':True}]; data=json.dumps(payload).encode(); req=urllib.request.Request('http://127.0.0.1:8000/api/v1/users/batch', data=data, headers={'Content-Type':'application/json','Authorization':'Bearer '+token}, method='POST'); res=json.loads(urllib.request.urlopen(req, timeout=5).read()); assert res['total'] == 1; assert res['succeeded'] == 1; assert res['results'][0]['changed'] is False; assert res['results'][0]['sync_records'] == 0"
  compose exec -T api python - <<'PY'
import json
import os
import urllib.error
import urllib.request

token = os.environ["MINGDAO_API_TOKEN"]
payload = [
    {"employee_record_id": f"batch-record-{index}", "employee_id": str(index), "pin": f"batch-pin-{index}", "name": f"User {index}", "department": "IT", "privilege": 0, "enabled": True}
    for index in range(501)
]
request = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/users/batch",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    method="POST",
)
try:
    urllib.request.urlopen(request, timeout=5)
    raise AssertionError("batch limit was not enforced")
except urllib.error.HTTPError as exc:
    assert exc.code == 413
PY

  user_count="$(compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -N -e "SELECT COUNT(*) FROM device_user WHERE employee_id='${TEST_EMPLOYEE_ID}';" 2>/dev/null | tr -d ' ')"
  if [ "${user_count}" != "1" ]; then
    log "Repeated identical POST created duplicate device_user rows."
    exit 1
  fi

  duplicate_sync_count="$(compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -N -e "SELECT COUNT(*) FROM (SELECT device_sn, COUNT(*) c FROM device_user_sync WHERE employee_id='${TEST_EMPLOYEE_ID}' GROUP BY device_sn HAVING c > 1) duplicated;" 2>/dev/null | tr -d ' ')"
  if [ "${duplicate_sync_count}" != "0" ]; then
    log "Repeated identical POST created duplicate device_user_sync rows."
    exit 1
  fi
}

verify_regression_routes() {
  log "Verifying GETREQUEST and Console regression"
  compose exec -T api python -c "import json, urllib.request; res=urllib.request.urlopen('http://127.0.0.1:8000/iclock/getrequest', timeout=5).read().decode(); assert res == 'OK'; data=json.loads(urllib.request.urlopen('http://127.0.0.1:8000/console?format=json&device_filter=all', timeout=5).read()); assert 'dashboard' in data; assert 'mingdao_sync' in data['dashboard']; assert 'user_upload' in data['dashboard']"
}

cleanup_test_data() {
  if [ -z "${MYSQL_USERNAME:-}" ] || [ -z "${MYSQL_PASSWORD:-}" ] || [ -z "${MYSQL_DATABASE:-}" ]; then
    return
  fi
  log "Cleaning install verification data"
  compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -e "DELETE FROM device_user_sync WHERE employee_id='${TEST_EMPLOYEE_ID}'; DELETE FROM device_user WHERE employee_id='${TEST_EMPLOYEE_ID}';" >/dev/null 2>&1 || true
}

main() {
  cd "${PROJECT_DIR}"
  trap cleanup_test_data EXIT
  ensure_env_file
  load_env
  verify_api_token
  scripts/DT009.83_install_ubuntu.sh "$@"
  load_env
  verify_tables
  verify_user_api
  verify_regression_routes
  cleanup_test_data
  trap - EXIT

  printf '\n'
  printf '========================================\n'
  printf 'Mingdao User Sync API Ready\n'
  printf 'API: POST /api/v1/users\n'
  printf 'API: POST /api/v1/users/batch\n'
  printf 'API: GET /api/v1/users\n'
  printf 'Application Ready\n'
  printf '========================================\n'
}

main "$@"
