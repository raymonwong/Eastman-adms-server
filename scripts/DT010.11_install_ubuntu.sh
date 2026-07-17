#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  printf '[DT010.11] %s\n' "$1" >&2
}

compose() {
  docker compose --env-file "${PROJECT_DIR}/.env" -f "${PROJECT_DIR}/docker-compose.yml" "$@"
}

verify_integration_console() {
  log "Verifying System Settings Integration page"
  compose exec -T api python - <<'PY'
import json
import time
import urllib.request


def read_url(url: str) -> str:
    last_error = None
    for attempt in range(1, 31):
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                return response.read().decode()
        except Exception as exc:
            last_error = exc
            print(f"Integration URL not ready yet, retry {attempt}/30: {url} ({exc})", flush=True)
            time.sleep(2)
    raise RuntimeError(f"Integration URL not ready after 30 retries: {url}") from last_error


html = read_url("http://127.0.0.1:8000/settings/integration")
assert "Mingdao Integration" in html
assert "Mingdao Configuration Guide" in html
assert "HTTP Request Examples" in html
assert "API Test" in html
assert "Open Integration Documentation" in html

data = json.loads(read_url("http://127.0.0.1:8000/api/settings/integration"))
assert data["system_name"] == "Mingdao"
assert data["api_base_url"].endswith("/api/v1")
assert data["authentication"] == "Bearer Token"
assert "token_masked" in data and data["token_value"] == ""
assert "last_api_response_code" in data
assert "total_api_requests" in data

health = json.loads(read_url("http://127.0.0.1:8000/api/settings/integration/health"))
assert health["api"] == "Running"
assert health["database"] == "Connected"
assert health["authentication"] in ("Enabled", "Disabled")

doc = read_url("http://127.0.0.1:8000/settings/integration/documentation")
assert "Mingdao API Integration" in doc
assert "POST /api/v1/users" in doc
PY
}

verify_docs() {
  log "Verifying Mingdao API integration document"
  if [ ! -f "${PROJECT_DIR}/docs/Mingdao_API_Integration.md" ]; then
    log "Missing docs/Mingdao_API_Integration.md"
    exit 1
  fi
}

main() {
  cd "${PROJECT_DIR}"
  scripts/DT010.1_install_ubuntu.sh "$@"
  verify_integration_console
  verify_docs

  printf '\n'
  printf '========================================\n'
  printf 'Integration Console Ready\n'
  printf 'Page: /settings/integration\n'
  printf 'Mingdao API Integration Ready\n'
  printf '========================================\n'
}

main "$@"
