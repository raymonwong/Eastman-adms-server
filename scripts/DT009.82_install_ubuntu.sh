#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  printf '[DT009.82] %s\n' "$1" >&2
}

compose() {
  docker compose --env-file "${PROJECT_DIR}/.env" -f "${PROJECT_DIR}/docker-compose.yml" "$@"
}

verify_console_data() {
  log "Verifying Console V2 data integration"
  compose exec -T api python -c "import json, urllib.request; data=json.loads(urllib.request.urlopen('http://127.0.0.1:8000/console?format=json&device_filter=all', timeout=5).read()); assert set(['server','filter','dashboard','latest_activity','events','device_summary']).issubset(data); assert len(data.get('latest_activity', [])) <= 5; assert len(data.get('events', [])) <= 10; assert all('show_in_console' not in row for row in data.get('device_summary', [])); assert all(opt['value'] == 'all' or opt['value'].startswith('device:') for opt in data['filter']['options'])"
}

main() {
  cd "${PROJECT_DIR}"
  scripts/DT009.81_install_ubuntu.sh "$@"
  verify_console_data

  printf '\n'
  printf '========================================\n'
  printf 'Console V2 Data Integration Ready\n'
  printf 'Console URL: http://SERVER_IP:4370/console\n'
  printf 'Application Ready\n'
  printf '========================================\n'
}

main "$@"
