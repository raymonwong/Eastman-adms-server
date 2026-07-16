#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  printf '[DT009.7] %s\n' "$1" >&2
}

compose() {
  docker compose --env-file "${PROJECT_DIR}/.env" -f "${PROJECT_DIR}/docker-compose.yml" "$@"
}

verify_device_management_ui() {
  log "Verifying Device Management optimized UI"
  compose exec -T api python -c "import urllib.request; html=urllib.request.urlopen('http://127.0.0.1:8000/dms', timeout=5).read().decode(); assert 'ON / 开启' in html; assert 'OFF / 关闭' in html; assert 'TRUE / 是' not in html; assert 'FALSE / 否' not in html; assert 'attendanceConfirmModal' in html"
}

main() {
  cd "${PROJECT_DIR}"
  scripts/DT009.6_install_ubuntu.sh "$@"
  verify_device_management_ui

  printf '\n'
  printf '========================================\n'
  printf 'Device Management Optimization Ready\n'
  printf 'Device Management URL: http://SERVER_IP:4370/dms\n'
  printf 'Application Ready\n'
  printf '========================================\n'
}

main "$@"
