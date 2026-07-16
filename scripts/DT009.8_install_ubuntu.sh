#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  printf '[DT009.8] %s\n' "$1" >&2
}

compose() {
  docker compose --env-file "${PROJECT_DIR}/.env" -f "${PROJECT_DIR}/docker-compose.yml" "$@"
}

verify_console_v2() {
  log "Verifying ADMS Server Console V2"
  compose exec -T api python -c "import urllib.request; html=urllib.request.urlopen('http://127.0.0.1:8000/console', timeout=5).read().decode(); assert 'ADMS Server Console V2' in html; assert 'Device Filter' in html; assert 'Device Summary' in html"
  compose exec -T api python -c "import json, urllib.request; data=json.loads(urllib.request.urlopen('http://127.0.0.1:8000/console?format=json&device_filter=all', timeout=5).read()); assert 'server' in data; assert 'filter' in data; assert 'dashboard' in data; assert 'latest_activity' in data; assert 'events' in data; assert 'device_summary' in data"
}

main() {
  cd "${PROJECT_DIR}"
  scripts/DT009.7_install_ubuntu.sh "$@"
  verify_console_v2

  printf '\n'
  printf '========================================\n'
  printf 'ADMS Server Console V2 Ready\n'
  printf 'Console URL: http://SERVER_IP:4370/console\n'
  printf 'Application Ready\n'
  printf '========================================\n'
}

main "$@"
