#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  echo "[DT017.1] $*"
}

main() {
  cd "${PROJECT_DIR}"

  log "Deploying current project"
  bash scripts/DT017_install_ubuntu.sh "$@"

  log "Restarting API with User Operation Guide"
  docker compose up -d --build api

  log "Verifying Help Center and User Operation Guide pages"
  docker compose exec -T api python - <<'PY'
import urllib.request

from app.main import app

routes = {route.path for route in app.routes}
assert "/settings/help" in routes
assert "/settings/user-guide" in routes

help_page = urllib.request.urlopen("http://127.0.0.1:8000/settings/help", timeout=10).read().decode("utf-8")
assert "Help Center" in help_page
assert "/settings/user-guide" in help_page

guide_page = urllib.request.urlopen("http://127.0.0.1:8000/settings/user-guide", timeout=10).read().decode("utf-8")
assert "HR Administrator Operations" in guide_page
assert "Add a New Employee" in guide_page
assert "Enroll Fingerprint" in guide_page
assert "Set Device Role" in guide_page
assert "Add a New Device" in guide_page
assert "languageSelect" in guide_page
PY

  echo "========================================"
  echo "DT017.1 User Operation Guide Ready"
  echo "Help Center: /settings/help"
  echo "User Guide: /settings/user-guide"
  echo "========================================"
}

main "$@"
