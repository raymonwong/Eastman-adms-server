#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  printf '[DT004] %s\n' "$1" >&2
}

compose() {
  docker compose --env-file "${PROJECT_DIR}/.env" -f "${PROJECT_DIR}/docker-compose.yml" "$@"
}

verify_initialization_handshake() {
  log "Verifying initialization handshake response builder"
  compose exec -T api python -c "from app.adms import _build_initialization_response; body=_build_initialization_response('DT004_CHECK'); assert body.startswith('GET OPTION FROM: DT004_CHECK'); assert 'TimeZone=4' in body; assert 'Realtime=1' in body; assert 'PushProtVer=2.4.2' in body; assert 'TransFlag=TransData' in body"
}

main() {
  cd "${PROJECT_DIR}"
  scripts/DT002_install_ubuntu.sh "$@"
  verify_initialization_handshake

  printf '\n'
  printf '========================================\n'
  printf 'Initialization Handshake Ready\n'
  printf 'Application Ready\n'
  printf '========================================\n'
}

main "$@"
