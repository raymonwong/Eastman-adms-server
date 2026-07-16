#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  printf '[DT009] %s\n' "$1" >&2
}

compose() {
  docker compose --env-file "${PROJECT_DIR}/.env" -f "${PROJECT_DIR}/docker-compose.yml" "$@"
}

verify_debug_logging() {
  log "Verifying ADMS debug logging helpers"
  compose exec -T api python -c "from app.adms import _debug_log; assert callable(_debug_log)"
}

main() {
  cd "${PROJECT_DIR}"
  scripts/DT008_install_ubuntu.sh "$@"
  verify_debug_logging

  printf '\n'
  printf '========================================\n'
  printf 'ADMS Debug Log Ready\n'
  printf 'Application Ready\n'
  printf '========================================\n'
}

main "$@"
