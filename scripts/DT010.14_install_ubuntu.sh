#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[DT010.14] %s\n' "$1" >&2
}

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  else
    docker-compose "$@"
  fi
}

verify_users_console() {
  log "Verifying ADMS Users Console page"
  compose exec -T api python - <<'PY'
import json
import urllib.request

html = urllib.request.urlopen("http://127.0.0.1:8000/users", timeout=5).read().decode()
assert "ADMS Users" in html
assert "Grouped by Department" in html

data = json.loads(urllib.request.urlopen("http://127.0.0.1:8000/api/adms-users", timeout=5).read())
assert isinstance(data, list)
PY
}

main() {
  cd "$(dirname "$0")/.."
  scripts/DT010.13_install_ubuntu.sh "$@"
  verify_users_console

  printf '==================================\n'
  printf 'DT010.14 ADMS Users Console Ready\n'
  printf 'Page: /users\n'
  printf 'API: /api/adms-users\n'
  printf 'Grouped by Department\n'
  printf '==================================\n'
}

main "$@"
