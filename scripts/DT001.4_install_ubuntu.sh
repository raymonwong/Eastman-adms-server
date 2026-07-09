#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${PROJECT_DIR}/.env"
ENV_EXAMPLE="${PROJECT_DIR}/.env.example"

log() {
  printf '[DT001.4] %s\n' "$1" >&2
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

verify_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    fail "Docker is not installed. Please install Docker before running DT001.4."
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

create_volumes() {
  docker volume create eastman-adms-mysql >/dev/null
  docker volume create eastman-adms-logs >/dev/null
  docker volume create eastman-adms-backup >/dev/null
  log "Docker volumes verified"
}

pull_required_images() {
  log "Pulling MySQL image: ${MYSQL_IMAGE}"
  if ! docker compose --env-file "${ENV_FILE}" -f "${PROJECT_DIR}/docker-compose.yml" pull mysql; then
    fail "docker compose pull failed for image: ${MYSQL_IMAGE}"
  fi

  # Docker Compose does not pull build-stage base images via service pull.
  log "Pulling Python base image: ${PYTHON_IMAGE}"
  if ! docker pull "${PYTHON_IMAGE}"; then
    fail "docker pull failed for image: ${PYTHON_IMAGE}"
  fi
}

start_services() {
  log "Starting Docker Compose services"
  docker compose --env-file "${ENV_FILE}" -f "${PROJECT_DIR}/docker-compose.yml" up -d
}

verify_running_service() {
  local service="$1"

  if ! docker compose --env-file "${ENV_FILE}" -f "${PROJECT_DIR}/docker-compose.yml" ps --status running --services | grep -Fxq "${service}"; then
    docker compose --env-file "${ENV_FILE}" -f "${PROJECT_DIR}/docker-compose.yml" ps
    fail "Service is not running: ${service}"
  fi
}

show_runtime_status() {
  log "docker compose ps"
  docker compose --env-file "${ENV_FILE}" -f "${PROJECT_DIR}/docker-compose.yml" ps

  log "docker ps"
  docker ps
}

main() {
  cd "${PROJECT_DIR}"

  ensure_env_file
  ensure_env_defaults
  load_env

  require_env MYSQL_IMAGE
  require_env PYTHON_IMAGE
  require_env API_IMAGE

  verify_docker
  verify_compose
  create_volumes
  pull_required_images
  start_services
  show_runtime_status
  verify_running_service mysql
  verify_running_service api

  printf '\n'
  printf 'Docker Running\n'
  printf 'MySQL Running\n'
  printf 'FastAPI Running\n'
  printf 'Install Completed\n'
}

main "$@"
