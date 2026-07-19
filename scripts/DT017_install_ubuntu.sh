#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  echo "[DT017] $*"
}

main() {
  cd "${PROJECT_DIR}"

  log "Deploying current project"
  bash scripts/DT016_install_ubuntu.sh "$@"

  log "Restarting API with Help Center"
  docker compose up -d --build api

  log "Verifying Help Center page"
  docker compose exec -T api python - <<'PY'
import urllib.request

from app.main import app

routes = {route.path for route in app.routes}
assert "/settings/help" in routes

page = urllib.request.urlopen("http://127.0.0.1:8000/settings/help", timeout=10).read().decode("utf-8")
assert "Help Center" in page
assert "System Functions" in page
assert "User Operation Guide" in page
assert "Add a New Employee" in page
assert "Enroll Fingerprint" in page
assert "Backup and Restore" in page
PY

  echo "========================================"
  echo "DT017 Help Center Ready"
  echo "Console Page: /settings/help"
  echo "========================================"
}

main "$@"
