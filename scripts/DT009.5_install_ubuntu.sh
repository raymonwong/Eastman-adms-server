#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  printf '[DT009.5] %s\n' "$1" >&2
}

compose() {
  docker compose --env-file "${PROJECT_DIR}/.env" -f "${PROJECT_DIR}/docker-compose.yml" "$@"
}

verify_console() {
  log "Verifying ADMS Server Console"
  compose exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/console', timeout=5).read()"
  compose exec -T api python -c "import json, urllib.request; data=json.loads(urllib.request.urlopen('http://127.0.0.1:8000/console?format=json', timeout=5).read()); assert 'server' in data; assert 'devices' in data; assert 'events' in data; assert 'statistics' in data"
}

main() {
  cd "${PROJECT_DIR}"
  scripts/DT009_install_ubuntu.sh "$@"
  verify_console

  printf '\n'
  printf '========================================\n'
  printf 'ADMS Server Console Ready\n'
  printf 'Console URL: http://SERVER_IP:4370/console\n'
  printf 'Application Ready\n'
  printf '========================================\n'
}

main "$@"
