#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  echo "[DT018] $*"
}

generate_secret() {
  if command -v python3 >/dev/null 2>&1; then
    python3 -c "import secrets; print(secrets.token_urlsafe(18))"
  elif command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 18
  else
    date +%s%N
  fi
}

ensure_console_auth_env() {
  local generated_password=""
  if ! grep -q '^CONSOLE_ADMIN_PASSWORD=' .env; then
    generated_password="$(generate_secret)"
    printf '\nCONSOLE_ADMIN_PASSWORD=%s\n' "${generated_password}" >> .env
  fi
  if ! grep -q '^CONSOLE_SESSION_SECRET=' .env; then
    printf 'CONSOLE_SESSION_SECRET=%s\n' "$(generate_secret)" >> .env
  fi
  if ! grep -q '^CONSOLE_SESSION_TTL_SECONDS=' .env; then
    printf 'CONSOLE_SESSION_TTL_SECONDS=43200\n' >> .env
  fi

  if [[ -n "${generated_password}" ]]; then
    log "Initial admin password generated: ${generated_password}"
    log "Please log in once and change it at /settings/password."
  fi
}

main() {
  cd "${PROJECT_DIR}"

  ensure_console_auth_env

  log "Restarting API with admin password protection"
  docker compose up -d --build api

  log "Verifying admin password routes and public exclusions"
  docker compose exec -T api python - <<'PY'
import urllib.error
import urllib.request

from app.main import app


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


routes = {route.path for route in app.routes}
assert "/login" in routes
assert "/settings/password" in routes
assert "/settings/help" in routes
assert "/settings/user-guide" in routes

login_page = urllib.request.urlopen("http://127.0.0.1:8000/login", timeout=10).read().decode("utf-8")
assert "ADMS Admin Login" in login_page

help_page = urllib.request.urlopen("http://127.0.0.1:8000/settings/help", timeout=10).read().decode("utf-8")
assert "Help Center" in help_page

guide_page = urllib.request.urlopen("http://127.0.0.1:8000/settings/user-guide", timeout=10).read().decode("utf-8")
assert "Help Center" in guide_page

opener = urllib.request.build_opener(NoRedirect)
try:
    opener.open("http://127.0.0.1:8000/console", timeout=10)
    raise AssertionError("/console should redirect to /login without an admin session")
except urllib.error.HTTPError as exc:
    assert exc.code in (302, 303, 307)
    assert "/login" in exc.headers.get("Location", "")

health = urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=10).read().decode("utf-8")
assert "ok" in health
PY

  echo "========================================"
  echo "DT018 Admin Password Protection Ready"
  echo "Login Page: /login"
  echo "Change Password: /settings/password"
  echo "Help Center remains public: /settings/help"
  echo "========================================"
}

main "$@"
