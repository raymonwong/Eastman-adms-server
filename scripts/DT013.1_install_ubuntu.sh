#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  echo "[DT013.1] $*"
}

compose() {
  docker compose "$@"
}

main() {
  cd "${PROJECT_DIR}"

  log "Deploying current project"
  bash scripts/DT010.12_install_ubuntu.sh "$@"

  log "Verifying Attendance Synchronization configuration API"
  compose exec -T api python - <<'PY'
import json
import urllib.error
import urllib.request

import app.main  # noqa: F401
from app.integration_settings import AttendanceIntegrationConfigRequest, _attendance_schema_url

payload = {
    "enabled": False,
    "openapi_url": "https://api.example.com",
    "app_key": "example-app-key",
    "sign": "example-sign",
    "worksheet_id": "worksheet001",
    "employee_record_id_field_id": "field_employee",
    "check_time_field_id": "field_check_time",
    "check_date_field_id": "field_check_date",
    "device_name_field_id": "field_device_name",
    "device_sn_field_id": "field_device_sn",
}
model = AttendanceIntegrationConfigRequest.model_validate(payload)
assert model.worksheet_id == "worksheet001"
assert _attendance_schema_url(payload["openapi_url"], payload["worksheet_id"]) == "https://api.example.com/v3/app/worksheets/worksheet001"

response = urllib.request.urlopen("http://127.0.0.1:8000/api/settings/integration", timeout=10)
data = json.loads(response.read().decode("utf-8"))
assert "attendance_sync" in data
assert "configured_fields" in data["attendance_sync"]

invalid_payload = payload | {"openapi_url": "", "worksheet_id": ""}
request = urllib.request.Request(
    "http://127.0.0.1:8000/api/settings/integration/attendance/test",
    data=json.dumps(invalid_payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
test_result = json.loads(urllib.request.urlopen(request, timeout=10).read().decode("utf-8"))
assert test_result["success"] is False
assert test_result["message"] == "Validation failed."
PY

  log "Verifying System Settings sub pages and documentation"
  compose exec -T api python - <<'PY'
import urllib.request

inbound_page = urllib.request.urlopen("http://127.0.0.1:8000/settings/integration", timeout=10).read().decode("utf-8")
assert "Inbound API" in inbound_page
assert "Mingdao Configuration Guide" in inbound_page
assert "API Token" in inbound_page
assert "Attendance Synchronization" not in inbound_page

attendance_page = urllib.request.urlopen("http://127.0.0.1:8000/settings/attendance-sync", timeout=10).read().decode("utf-8")
assert "Attendance Synchronization" in attendance_page
assert "Mingdao Attendance OpenAPI URL" in attendance_page
assert "Test Connection" in attendance_page
assert "attendance_event.id" in attendance_page
assert "Mingdao Configuration Guide" not in attendance_page

doc = urllib.request.urlopen("http://127.0.0.1:8000/settings/integration/documentation", timeout=10).read().decode("utf-8")
assert "Attendance Synchronization Configuration" in doc
assert "HAP-Appkey" in doc
assert "attendance_event.id" in doc
PY

  echo "========================================"
  echo "DT013.1 Attendance Integration Config Ready"
  echo "Inbound API Page: /settings/integration"
  echo "Attendance Sync Page: /settings/attendance-sync"
  echo "No attendance records uploaded"
  echo "========================================"
}

main "$@"
