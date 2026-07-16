#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  printf '[DT009.83] %s\n' "$1" >&2
}

compose() {
  docker compose --env-file "${PROJECT_DIR}/.env" -f "${PROJECT_DIR}/docker-compose.yml" "$@"
}

verify_console_p0() {
  log "Verifying Console P0 UX logic"
  compose exec -T api python -c "import json, urllib.request; data=json.loads(urllib.request.urlopen('http://127.0.0.1:8000/console?format=json&device_filter=all', timeout=5).read()); assert set(['server','filter','dashboard','latest_activity','events','device_summary']).issubset(data); assert all(opt['value'] == 'all' or opt['value'].startswith('device:') for opt in data['filter']['options']); assert all('device_sn' in row and 'device_display' in row for row in data.get('device_summary', [])); assert all('device_sn' in item and 'device_display' in item for item in data.get('latest_activity', [])); assert all('device_sn' in event and 'device_display' in event for event in data.get('events', []))"
  compose exec -T api python -c "import urllib.request; html=urllib.request.urlopen('http://127.0.0.1:8000/console', timeout=5).read().decode(); assert '正在加载' in html; assert '加载失败' in html; assert '当前筛选最近10条' in html"
}

main() {
  cd "${PROJECT_DIR}"
  scripts/DT009.82_install_ubuntu.sh "$@"
  verify_console_p0

  printf '\n'
  printf '========================================\n'
  printf 'Console P0 UX Logic Ready\n'
  printf 'Console URL: http://SERVER_IP:4370/console\n'
  printf 'Device Management URL: http://SERVER_IP:4370/dms\n'
  printf 'Application Ready\n'
  printf '========================================\n'
}

main "$@"
