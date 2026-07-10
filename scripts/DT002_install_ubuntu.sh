#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${PROJECT_DIR}/.env"
ENV_EXAMPLE="${PROJECT_DIR}/.env.example"
RESET_DB=0
DIAGNOSTICS_PRINTED=0
REQUIRED_TABLES=("device" "attendance" "raw_request" "sync_log")

log() {
  printf '[DT002] %s\n' "$1" >&2
}

fail() {
  log "$1"
  print_diagnostics
  exit 1
}

parse_args() {
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --reset-db)
        RESET_DB=1
        ;;
      *)
        fail "Unknown argument: $1"
        ;;
    esac
    shift
  done
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
    ""|changeme|changeit|changeplease|pleaseme|pleasechangeme|password|password123|123456|12345678|mysqlpassword|default|defaultpassword|apppassword|pleasechangeme|changemeapppassword|changeappassword|changemeappassword)
      printf '[DT002] WARNING: MYSQL_PASSWORD uses a default development placeholder. Please modify MYSQL_PASSWORD before production deployment.\n' >&2
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

print_diagnostics() {
  if [ "${DIAGNOSTICS_PRINTED}" -eq 1 ]; then
    return
  fi
  DIAGNOSTICS_PRINTED=1

  printf '\n[DT002] Deployment diagnostics\n' >&2

  if command -v docker >/dev/null 2>&1; then
    compose ps >&2 || true
    docker ps >&2 || true
    docker logs --tail 100 eastman-adms-mysql >&2 || true
    docker logs --tail 100 eastman-adms-api >&2 || true
  else
    printf '[DT002] Docker command is not available.\n' >&2
  fi
}

reset_database_if_requested() {
  if [ "${RESET_DB}" -ne 1 ]; then
    return
  fi

  log "Reset database mode enabled. This removes the MySQL Docker volume."
  compose down
  docker volume rm eastman-adms-mysql >/dev/null 2>&1 || true
}

pull_images() {
  log "Pulling MySQL image: ${MYSQL_IMAGE}"
  if ! compose pull mysql; then
    fail "docker compose pull failed for image: ${MYSQL_IMAGE}"
  fi

  log "Pulling Python base image: ${PYTHON_IMAGE}"
  if ! docker pull "${PYTHON_IMAGE}"; then
    fail "docker pull failed for image: ${PYTHON_IMAGE}"
  fi
}

restart_containers() {
  log "Building project images with latest base images"
  compose build --pull

  log "Restarting API container with rebuilt project image"
  compose up -d --force-recreate api
}

wait_for_mysql() {
  local attempt

  log "Waiting for MySQL health"
  for attempt in $(seq 1 30); do
    if [ "$(docker inspect -f '{{.State.Health.Status}}' eastman-adms-mysql 2>/dev/null || true)" = "healthy" ]; then
      return
    fi

    log "MySQL not healthy yet, retry ${attempt}/30"
    sleep 2
  done

  fail "MySQL health verification failed."
}

verify_database_tables() {
  local table
  local tables

  log "Verifying database tables with SHOW TABLES"
  tables="$(compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -N -e "SHOW TABLES;" 2>/dev/null || true)"

  for table in "${REQUIRED_TABLES[@]}"; do
    if ! printf '%s\n' "${tables}" | grep -Fxq "${table}"; then
      fail "Required database table is missing: ${table}"
    fi
  done
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

on_error() {
  local exit_code=$?
  printf '\n[DT002] Deployment failed with exit code %s.\n' "${exit_code}" >&2
  print_diagnostics
  exit "${exit_code}"
}

main() {
  trap on_error ERR
  cd "${PROJECT_DIR}"

  parse_args "$@"
  ensure_env_file
  ensure_env_defaults
  load_env

  require_env MYSQL_IMAGE
  require_env PYTHON_IMAGE
  require_env API_IMAGE
  require_env MYSQL_USERNAME
  require_env MYSQL_PASSWORD
  require_env MYSQL_DATABASE
  validate_mysql_password

  verify_docker
  verify_compose
  reset_database_if_requested
  pull_images
  restart_containers
  wait_for_mysql
  verify_health_api
  verify_database_tables

  printf '\n'
  printf '========================================\n'
  printf 'Database Ready\n'
  printf 'Application Ready\n'
  printf '========================================\n'
}

main "$@"
