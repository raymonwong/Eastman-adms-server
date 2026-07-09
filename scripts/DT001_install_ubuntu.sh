#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${PROJECT_DIR}/.env"
ENV_EXAMPLE="${PROJECT_DIR}/.env.example"

log() {
  printf '[DT001] %s\n' "$1"
}

require_ubuntu() {
  if [ ! -f /etc/os-release ]; then
    log "Cannot find /etc/os-release"
    exit 1
  fi

  # shellcheck disable=SC1091
  . /etc/os-release
  if [ "${ID:-}" != "ubuntu" ]; then
    log "Ubuntu is required. Detected: ${PRETTY_NAME:-unknown}"
    exit 1
  fi
}

ensure_project_dirs() {
  mkdir -p \
    "${PROJECT_DIR}/app" \
    "${PROJECT_DIR}/config" \
    "${PROJECT_DIR}/logs" \
    "${PROJECT_DIR}/backup" \
    "${PROJECT_DIR}/mysql" \
    "${PROJECT_DIR}/scripts" \
    "${PROJECT_DIR}/docs"
}

ensure_env_file() {
  if [ ! -f "${ENV_FILE}" ]; then
    cp "${ENV_EXAMPLE}" "${ENV_FILE}"
    log "Created .env from .env.example"
  else
    log ".env already exists"
  fi
}

load_env() {
  set -a
  # shellcheck disable=SC1090
  . "${ENV_FILE}"
  set +a
}

install_docker_if_missing() {
  if command -v docker >/dev/null 2>&1; then
    log "Docker already installed"
    return
  fi

  log "Installing latest Docker Engine"
  sudo apt-get update
  sudo apt-get install -y ca-certificates curl
  sudo install -m 0755 -d /etc/apt/keyrings

  if [ ! -f /etc/apt/keyrings/docker.asc ]; then
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc
  fi

  local codename
  codename="$(
    # shellcheck disable=SC1091
    . /etc/os-release && printf '%s' "${VERSION_CODENAME}"
  )"

  local source_file="/etc/apt/sources.list.d/docker.list"
  local source_line
  source_line="deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${codename} stable"

  if [ ! -f "${source_file}" ] || ! grep -Fxq "${source_line}" "${source_file}"; then
    printf '%s\n' "${source_line}" | sudo tee "${source_file}" >/dev/null
  fi

  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
}

install_compose_if_missing() {
  if docker compose version >/dev/null 2>&1; then
    log "Docker Compose already installed"
    return
  fi

  log "Installing Docker Compose plugin"
  sudo apt-get update
  sudo apt-get install -y docker-compose-plugin
}

ensure_docker_running() {
  sudo systemctl enable docker
  sudo systemctl start docker
}

create_docker_volumes() {
  sudo docker volume create eastman-adms-mysql >/dev/null
  sudo docker volume create eastman-adms-logs >/dev/null
  sudo docker volume create eastman-adms-backup >/dev/null
}

start_services() {
  cd "${PROJECT_DIR}"
  sudo docker compose --env-file "${ENV_FILE}" up -d --build mysql
  sudo docker compose --env-file "${ENV_FILE}" up -d --build api
}

wait_for_mysql() {
  local attempts=60
  while [ "${attempts}" -gt 0 ]; do
    if sudo docker compose --env-file "${ENV_FILE}" exec -T mysql mysqladmin ping -h 127.0.0.1 -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" --silent >/dev/null 2>&1; then
      return 0
    fi
    attempts=$((attempts - 1))
    sleep 2
  done

  log "MySQL did not become ready"
  return 1
}

wait_for_fastapi() {
  local attempts=60
  local url="http://127.0.0.1:${APP_PORT}/health"
  while [ "${attempts}" -gt 0 ]; do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      return 0
    fi
    attempts=$((attempts - 1))
    sleep 2
  done

  log "FastAPI did not become ready"
  return 1
}

print_result() {
  printf '%s\n' "=================================="
  printf '%s\n' "Eastman ADMS Server"
  printf '%s\n' "Docker ............. OK"
  printf '%s\n' "MySQL .............. OK"
  printf '%s\n' "FastAPI ............ OK"
  printf '%s\n' "Install Completed"
  printf '%s\n' "=================================="
}

main() {
  require_ubuntu
  ensure_project_dirs
  ensure_env_file
  load_env
  install_docker_if_missing
  install_compose_if_missing
  ensure_docker_running
  create_docker_volumes
  start_services
  wait_for_mysql
  wait_for_fastapi
  print_result
}

main "$@"
