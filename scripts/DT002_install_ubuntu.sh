#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${PROJECT_DIR}/.env"
ENV_EXAMPLE="${PROJECT_DIR}/.env.example"

log() {
  printf '[DT002] %s\n' "$1" >&2
}

fail() {
  log "$1"
  exit 1
}

ensure_env_file() {
  if [ ! -f "${ENV_EXAMPLE}" ]; then
    fail ".env.example not found"
  fi

  if [ ! -f "${ENV_FILE}" ]; then
    cp "${ENV_EXAMPLE}" "${ENV_FILE}"
    log "Created .env from .env.example"
  else
    log ".env already exists"
  fi
}

ensure_env_default() {
  local name="$1"
  local default_line

  if grep -Eq "^${name}=" "${ENV_FILE}"; then
    return
  fi

  default_line="$(grep -E "^${name}=" "${ENV_EXAMPLE}" | tail -n 1 || true)"
  if [ -z "${default_line}" ]; then
    fail "Default environment variable is missing from .env.example: ${name}"
  fi

  printf '\n%s\n' "${default_line}" >> "${ENV_FILE}"
  log "Added missing ${name} to .env"
}

ensure_env_defaults() {
  ensure_env_default MYSQL_IMAGE
  ensure_env_default PYTHON_IMAGE
  ensure_env_default API_IMAGE
}

upgrade_default_api_image() {
  if grep -Fxq "API_IMAGE=eastman-adms-server:dt001" "${ENV_FILE}"; then
    sed -i "s/^API_IMAGE=eastman-adms-server:dt001$/API_IMAGE=eastman-adms-server:dt002/" "${ENV_FILE}"
    log "Updated API_IMAGE default from dt001 to dt002"
  fi
}

load_env() {
  set -a
  # shellcheck disable=SC1090
  . "${ENV_FILE}"
  set +a
}

require_env() {
  local name="$1"
  local value="${!name:-}"

  if [ -z "${value}" ]; then
    fail "Required environment variable is empty: ${name}"
  fi
}

validate_mysql_password() {
  local normalized
  normalized="$(printf '%s' "${MYSQL_PASSWORD:-}" | tr '[:upper:]' '[:lower:]' | tr -d ' _-')"

  case "${normalized}" in
    ""|changeme|changeit|changeplease|pleaseme|pleasechangeme|password|password123|123456|12345678|mysqlpassword|default|defaultpassword|apppassword|changemeapppassword|changeappassword|changemeappassword)
      printf 'Please change MYSQL_PASSWORD before deployment.\n' >&2
      exit 1
      ;;
  esac
}

compose() {
  docker compose --env-file "${ENV_FILE}" -f "${PROJECT_DIR}/docker-compose.yml" "$@"
}

verify_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    fail "Docker is not installed."
  fi

  if ! docker info >/dev/null 2>&1; then
    fail "Docker is installed but not running or not accessible."
  fi

  log "Docker verified"
}

verify_compose() {
  if ! docker compose version >/dev/null 2>&1; then
    fail "Docker Compose plugin is not installed or not accessible."
  fi

  log "Docker Compose verified"
}

pull_images() {
  log "Pulling MySQL image: ${MYSQL_IMAGE}"
  if ! compose pull mysql; then
    fail "docker compose pull failed for image: ${MYSQL_IMAGE}"
  fi

  # The API image is built locally, so pull the Dockerfile base image before rebuild.
  log "Pulling Python base image: ${PYTHON_IMAGE}"
  if ! docker pull "${PYTHON_IMAGE}"; then
    fail "docker pull failed for image: ${PYTHON_IMAGE}"
  fi
}

restart_containers() {
  log "Building API image: ${API_IMAGE}"
  compose build --pull api

  log "Restarting containers"
  compose up -d --force-recreate
}

verify_database_connection() {
  local attempt

  log "Verifying database connection"
  for attempt in $(seq 1 30); do
    if compose exec -T api python -c "from app.database import check_database_connection, create_database_engine; from app.settings import Settings; check_database_connection(create_database_engine(Settings.from_env()))"; then
      return
    fi

    log "Database not ready yet, retry ${attempt}/30"
    sleep 2
  done

  fail "Database connection verification failed."
}

verify_health_api() {
  local attempt

  log "Verifying Health API"
  for attempt in $(seq 1 30); do
    if compose exec -T api python -c "import json, urllib.request; data=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=10)); assert data['project']=='eastman-adms-server'; assert data['version']=='0.0.2'; assert data['status']=='running'; assert data['database']=='connected'"; then
      return
    fi

    log "Health API not ready yet, retry ${attempt}/30"
    sleep 2
  done

  fail "Health API verification failed."
}

main() {
  cd "${PROJECT_DIR}"

  ensure_env_file
  ensure_env_defaults
  upgrade_default_api_image
  load_env

  require_env MYSQL_IMAGE
  require_env PYTHON_IMAGE
  require_env API_IMAGE
  require_env MYSQL_PASSWORD
  validate_mysql_password

  verify_docker
  verify_compose
  pull_images
  restart_containers
  verify_database_connection
  verify_health_api

  printf '\n'
  printf '========================================\n'
  printf 'Database Ready\n'
  printf 'Application Ready\n'
  printf '========================================\n'
}

main "$@"
