#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${PROJECT_DIR}/.env"
ENV_EXAMPLE="${PROJECT_DIR}/.env.example"
PACKAGE_MANAGER=""
OS_ID=""
OS_VERSION_ID=""
OS_PRETTY_NAME=""

log() {
  printf '[DT001.2] %s\n' "$1"
}

detect_os() {
  if [ ! -f /etc/os-release ]; then
    log "Cannot find /etc/os-release"
    exit 1
  fi

  # shellcheck disable=SC1091
  . /etc/os-release
  OS_ID="${ID:-}"
  OS_VERSION_ID="${VERSION_ID:-}"
  OS_PRETTY_NAME="${PRETTY_NAME:-unknown}"
}

version_major() {
  printf '%s' "$1" | cut -d. -f1
}

is_rhel_compatible() {
  case "${OS_ID}" in
    alinux|anolis|rhel|centos|rocky|almalinux|ol|fedora)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

require_supported_os() {
  detect_os

  if [ "${OS_ID}" = "ubuntu" ] && [ "$(version_major "${OS_VERSION_ID}")" -ge 22 ]; then
    return
  fi

  if [ "${OS_ID}" = "alinux" ] && [ "$(version_major "${OS_VERSION_ID}")" -ge 3 ]; then
    return
  fi

  if is_rhel_compatible; then
    return
  fi

  log "Unsupported operating system: ${OS_PRETTY_NAME}"
  exit 1
}

detect_package_manager() {
  if command -v apt-get >/dev/null 2>&1; then
    PACKAGE_MANAGER="apt"
    return
  fi

  if command -v dnf >/dev/null 2>&1; then
    PACKAGE_MANAGER="dnf"
    return
  fi

  if command -v yum >/dev/null 2>&1; then
    PACKAGE_MANAGER="yum"
    return
  fi

  log "No supported package manager found. Expected apt, dnf, or yum."
  exit 1
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

install_docker_apt() {
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

install_docker_rhel() {
  local pm="$1"
  sudo "${pm}" install -y yum-utils ca-certificates curl

  if ! sudo "${pm}" repolist | grep -qi docker; then
    sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
  fi

  sudo "${pm}" install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
}

install_docker_if_missing() {
  if command -v docker >/dev/null 2>&1; then
    log "Docker already installed"
    return
  fi

  log "Installing Docker Engine using ${PACKAGE_MANAGER}"
  case "${PACKAGE_MANAGER}" in
    apt)
      install_docker_apt
      ;;
    dnf|yum)
      install_docker_rhel "${PACKAGE_MANAGER}"
      ;;
    *)
      log "Unsupported package manager: ${PACKAGE_MANAGER}"
      exit 1
      ;;
  esac
}

install_compose_if_missing() {
  if docker compose version >/dev/null 2>&1; then
    log "Docker Compose already installed"
    return
  fi

  log "Installing Docker Compose plugin using ${PACKAGE_MANAGER}"
  case "${PACKAGE_MANAGER}" in
    apt)
      sudo apt-get update
      sudo apt-get install -y docker-compose-plugin
      ;;
    dnf|yum)
      sudo "${PACKAGE_MANAGER}" install -y docker-compose-plugin
      ;;
    *)
      log "Unsupported package manager: ${PACKAGE_MANAGER}"
      exit 1
      ;;
  esac
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
  require_supported_os
  detect_package_manager
  log "Detected OS: ${OS_PRETTY_NAME}"
  log "Detected package manager: ${PACKAGE_MANAGER}"
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

