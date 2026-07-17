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
  compose exec -T api python -c "import urllib.request; html=urllib.request.urlopen('http://127.0.0.1:8000/settings/integration', timeout=5).read().decode(); assert 'Mingdao Integration' in html; assert 'Integration Guide' in html; assert 'HTTP Request Examples' in html"
  compose exec -T api python -c "import json, urllib.request; data=json.loads(urllib.request.urlopen('http://127.0.0.1:8000/api/settings/integration', timeout=5).read()); assert data['system_name'] == 'Mingdao'; assert data['api_base_url'].endswith('/api/v1'); assert data['authentication'] == 'Bearer Token'; assert 'token_masked' in data"
  compose exec -T api python -c "import json, urllib.request; data=json.loads(urllib.request.urlopen('http://127.0.0.1:8000/api/settings/integration/health', timeout=5).read()); assert data['api'] == 'Running'; assert data['database'] == 'Connected'; assert data['authentication'] in ('Enabled','Disabled')"
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
