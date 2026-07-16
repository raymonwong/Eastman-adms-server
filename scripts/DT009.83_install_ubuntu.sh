#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  printf '[DT009.83] %s\n' "$1" >&2
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

verify_device_management_columns() {
  local column_count

  log "Verifying device management columns"
  column_count="$(compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -N -e "SHOW COLUMNS FROM device WHERE Field IN ('location','record_attendance','show_in_console');" 2>/dev/null | wc -l | tr -d ' ')"
  if [ "${column_count}" != "3" ]; then
    log "Required device management columns are missing."
    exit 1
  fi
}

verify_console_p0() {
  log "Verifying Console P0/P1/P2 UX logic"
  compose exec -T api python -c "import json, urllib.request; data=json.loads(urllib.request.urlopen('http://127.0.0.1:8000/console?format=json&device_filter=all', timeout=5).read()); assert set(['server','filter','dashboard','exception_overview','heartbeat_summary','latest_activity','events','device_summary']).issubset(data); assert len(data.get('latest_activity', [])) <= 7; assert all(opt['value'] == 'all' or opt['value'].startswith('device:') for opt in data['filter']['options']); assert all('device_sn' in row and 'device_display' in row and 'show_in_console' in row for row in data.get('device_summary', [])); assert all('device_sn' in item and 'device_display' in item for item in data.get('latest_activity', [])); assert all('device_sn' in event and 'device_display' in event for event in data.get('events', []))"
  compose exec -T api python -c "import urllib.request; html=urllib.request.urlopen('http://127.0.0.1:8000/console', timeout=5).read().decode(); assert '正在加载' in html; assert '加载失败' in html; assert '当前筛选最近10条' in html"
  compose exec -T api python -c "import urllib.request; html=urllib.request.urlopen('http://127.0.0.1:8000/dms', timeout=5).read().decode(); assert 'Loading' in html; assert 'Load failed' in html; assert 'Device Management' in html; assert 'zh-sub' in html"
  compose exec -T api python -c "import urllib.request; html=urllib.request.urlopen('http://127.0.0.1:8000/console', timeout=5).read().decode(); assert 'Important Events' in html; assert 'Pause' in html; assert 'Technical Details' in html; assert 'Clear Current Log' in html; assert 'flashNewRow' in html"
  compose exec -T api python -c "import urllib.request; html=urllib.request.urlopen('http://127.0.0.1:8000/console', timeout=5).read().decode(); assert 'Operation Monitor' in html; assert 'Exception Priority' in html; assert 'summaryStatusFilter' in html; assert 'summarySort' in html; assert 'formatEmployeePin' in html; assert 'full-time' in html; assert 'Last 7 for current filter' in html; assert 'Protocol Console' in html and '开发中' in html"
  compose exec -T api python -c "import urllib.request; html=urllib.request.urlopen('http://127.0.0.1:8000/dms', timeout=5).read().decode(); assert 'Discard unsaved changes' in html; assert 'Saving' in html; assert 'When disabled, the device can still connect' in html"
}

main() {
  cd "${PROJECT_DIR}"
  scripts/DT009_install_ubuntu.sh "$@"
  load_env
  verify_device_management_columns
  verify_console_p0

  printf '\n'
  printf '========================================\n'
  printf 'Console P2 UX Ready\n'
  printf 'Console URL: http://SERVER_IP:4370/console\n'
  printf 'Device Management URL: http://SERVER_IP:4370/dms\n'
  printf 'Application Ready\n'
  printf '========================================\n'
}

main "$@"
