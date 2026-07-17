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
  local attempt
  for attempt in $(seq 1 30); do
    if compose exec -T api python -c "import urllib.request; assert urllib.request.urlopen('http://127.0.0.1:8000/settings/integration', timeout=5).status == 200" >/dev/null 2>&1; then
      break
    fi
    if [ "${attempt}" = "30" ]; then
      log "Integration page is not ready after 30 retries."
      exit 1
    fi
    log "Integration page not ready yet, retry ${attempt}/30"
    sleep 2
  done
  compose exec -T api python -c "import urllib.request; html=urllib.request.urlopen('http://127.0.0.1:8000/settings/integration', timeout=5).read().decode(); assert 'Mingdao Integration' in html; assert 'Mingdao Configuration Guide' in html; assert 'HTTP Request Examples' in html; assert 'API Test' in html; assert 'Open Integration Documentation' in html"
  compose exec -T api python -c "import json, urllib.request; data=json.loads(urllib.request.urlopen('http://127.0.0.1:8000/api/settings/integration', timeout=5).read()); assert data['system_name'] == 'Mingdao'; assert data['api_base_url'].endswith('/api/v1'); assert data['authentication'] == 'Bearer Token'; assert 'token_masked' in data and data['token_value'] == ''; assert 'last_api_response_code' in data; assert 'total_api_requests' in data"
  compose exec -T api python -c "import json, urllib.request; data=json.loads(urllib.request.urlopen('http://127.0.0.1:8000/api/settings/integration/health', timeout=5).read()); assert data['api'] == 'Running'; assert data['database'] == 'Connected'; assert data['authentication'] in ('Enabled','Disabled')"
  compose exec -T api python -c "import urllib.request; doc=urllib.request.urlopen('http://127.0.0.1:8000/settings/integration/documentation', timeout=5).read().decode(); assert 'Mingdao API Integration' in doc; assert 'POST /api/v1/users' in doc"
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
