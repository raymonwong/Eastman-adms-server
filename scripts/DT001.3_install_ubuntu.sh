#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${PROJECT_DIR}/.env"
ENV_EXAMPLE="${PROJECT_DIR}/.env.example"
PACKAGE_MANAGER=""
OS_ID=""
OS_ID_LIKE=""
OS_VERSION_ID=""
OS_VERSION_CODENAME=""
OS_PRETTY_NAME=""
SUDO=()
DOCKER_DAEMON_JSON="/etc/docker/daemon.json"
DOCKER_HUB_TEST_URL="https://registry-1.docker.io/v2/"
DOCKER_HUB_TIMEOUT_SECONDS="${DOCKER_HUB_TIMEOUT_SECONDS:-8}"
DOCKER_COMPOSE_PULL_RETRIES="${DOCKER_COMPOSE_PULL_RETRIES:-3}"

log() {
  printf '[DT001.3] %s\n' "$1" >&2
}

detect_os() {
  if [ ! -f /etc/os-release ]; then
    log "Cannot find /etc/os-release"
    exit 1
  fi

  # shellcheck disable=SC1091
  . /etc/os-release
  OS_ID="${ID:-}"
  OS_ID_LIKE="${ID_LIKE:-}"
  OS_VERSION_ID="${VERSION_ID:-}"
  OS_VERSION_CODENAME="${VERSION_CODENAME:-}"
  OS_PRETTY_NAME="${PRETTY_NAME:-unknown}"
}

version_major() {
  local major
  major="$(printf '%s' "${1:-0}" | cut -d. -f1 | tr -cd '0-9')"
  printf '%s' "${major:-0}"
}

is_rhel_compatible() {
  case "${OS_ID}" in
    alinux|anolis|openanolis|rhel|centos|rocky|almalinux|ol|fedora)
      return 0
      ;;
  esac

  case " ${OS_ID_LIKE} " in
    *" rhel "*|*" fedora "*|*" centos "*)
      return 0
      ;;
  esac

  return 1
}

require_supported_os() {
  detect_os

  if [ "${OS_ID}" = "ubuntu" ] && [ "$(version_major "${OS_VERSION_ID}")" -ge 22 ]; then
    return
  fi

  if [ "${OS_ID}" = "alinux" ] && [ "$(version_major "${OS_VERSION_ID}")" -ge 3 ]; then
    return
  fi

  if [ "${OS_ID}" = "openanolis" ] || [ "${OS_ID}" = "anolis" ]; then
    return
  fi

  if is_rhel_compatible; then
    return
  fi

  log "Unsupported operating system: ${OS_PRETTY_NAME}"
  exit 1
}

init_privilege() {
  if [ "$(id -u)" -eq 0 ]; then
    SUDO=()
    return
  fi

  if ! command -v sudo >/dev/null 2>&1; then
    log "Root permission is required. Please run as root or install sudo."
    exit 1
  fi

  SUDO=(sudo)
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

ensure_network_tools() {
  if command -v curl >/dev/null 2>&1; then
    return
  fi

  log "Installing curl and CA certificates using ${PACKAGE_MANAGER}"
  case "${PACKAGE_MANAGER}" in
    apt)
      "${SUDO[@]}" apt-get update
      "${SUDO[@]}" apt-get install -y ca-certificates curl
      ;;
    dnf|yum)
      "${SUDO[@]}" "${PACKAGE_MANAGER}" install -y ca-certificates curl
      ;;
    *)
      log "Unsupported package manager: ${PACKAGE_MANAGER}"
      exit 1
      ;;
  esac
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
  "${SUDO[@]}" apt-get update
  "${SUDO[@]}" apt-get install -y ca-certificates curl
  "${SUDO[@]}" install -m 0755 -d /etc/apt/keyrings

  if [ ! -f /etc/apt/keyrings/docker.asc ]; then
    "${SUDO[@]}" curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    "${SUDO[@]}" chmod a+r /etc/apt/keyrings/docker.asc
  fi

  local codename
  codename="${OS_VERSION_CODENAME}"
  if [ -z "${codename}" ]; then
    case "$(version_major "${OS_VERSION_ID}")" in
      22) codename="jammy" ;;
      24) codename="noble" ;;
      *)
        log "Cannot determine Ubuntu codename for ${OS_PRETTY_NAME}"
        exit 1
        ;;
    esac
  fi

  local source_file="/etc/apt/sources.list.d/docker.list"
  local source_line
  source_line="deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${codename} stable"

  if [ ! -f "${source_file}" ] || ! grep -Fxq "${source_line}" "${source_file}"; then
    printf '%s\n' "${source_line}" | "${SUDO[@]}" tee "${source_file}" >/dev/null
  fi

  "${SUDO[@]}" apt-get update
  "${SUDO[@]}" apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
}

docker_rhel_repo_release() {
  local major
  major="$(version_major "${OS_VERSION_ID}")"

  case "${OS_ID}" in
    alinux|anolis|openanolis)
      printf '%s' "8"
      return
      ;;
  esac

  if [ "${major}" -ge 9 ]; then
    printf '%s' "9"
  else
    printf '%s' "8"
  fi
}

install_rhel_base_packages() {
  local pm="$1"
  "${SUDO[@]}" "${pm}" install -y ca-certificates curl
}

ensure_docker_rhel_repo() {
  local repo_file="/etc/yum.repos.d/docker-ce.repo"
  local repo_release
  repo_release="$(docker_rhel_repo_release)"

  if [ -f "${repo_file}" ] && grep -q "download.docker.com/linux/centos" "${repo_file}"; then
    return
  fi

  log "Configuring Docker CE repository for CentOS/RHEL ${repo_release} compatibility"
  "${SUDO[@]}" mkdir -p /etc/yum.repos.d
  "${SUDO[@]}" tee "${repo_file}" >/dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://download.docker.com/linux/centos/${repo_release}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://download.docker.com/linux/centos/gpg
EOF
}

install_docker_rhel() {
  local pm="$1"
  install_rhel_base_packages "${pm}"
  ensure_docker_rhel_repo

  "${SUDO[@]}" "${pm}" makecache -y || "${SUDO[@]}" "${pm}" makecache

  if ! "${SUDO[@]}" "${pm}" install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin; then
    log "Docker CE packages failed to install. Trying distribution Docker packages."
    "${SUDO[@]}" "${pm}" install -y docker docker-compose-plugin
  fi
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
      "${SUDO[@]}" apt-get update
      "${SUDO[@]}" apt-get install -y docker-compose-plugin
      ;;
    dnf|yum)
      ensure_docker_rhel_repo
      "${SUDO[@]}" "${PACKAGE_MANAGER}" install -y docker-compose-plugin
      ;;
    *)
      log "Unsupported package manager: ${PACKAGE_MANAGER}"
      exit 1
      ;;
  esac
}

ensure_docker_running() {
  if command -v systemctl >/dev/null 2>&1; then
    "${SUDO[@]}" systemctl enable docker
    "${SUDO[@]}" systemctl start docker
    return
  fi

  if command -v service >/dev/null 2>&1; then
    "${SUDO[@]}" service docker start
    return
  fi

  log "Cannot start Docker automatically because systemctl/service is unavailable."
  exit 1
}

restart_docker() {
  log "Restarting Docker..."
  if command -v systemctl >/dev/null 2>&1; then
    "${SUDO[@]}" systemctl restart docker
    return
  fi

  if command -v service >/dev/null 2>&1; then
    "${SUDO[@]}" service docker restart
    return
  fi

  log "Cannot restart Docker automatically because systemctl/service is unavailable."
  exit 1
}

docker_hub_reachable() {
  log "Checking Docker Registry..."
  # Docker Hub returns 401 for anonymous /v2/ access; that still proves network reachability.
  local status
  status="$(curl -L -sS -o /dev/null -w '%{http_code}' --connect-timeout "${DOCKER_HUB_TIMEOUT_SECONDS}" --max-time "${DOCKER_HUB_TIMEOUT_SECONDS}" "${DOCKER_HUB_TEST_URL}" || true)"

  case "${status}" in
    200|401)
      log "Docker Hub reachable."
      return 0
      ;;
    *)
      log "Docker Hub unreachable or timed out. HTTP status: ${status:-none}"
      return 1
      ;;
  esac
}

docker_mirror_candidates() {
  if [ -n "${DOCKER_REGISTRY_MIRROR:-}" ]; then
    printf '%s\n' "${DOCKER_REGISTRY_MIRROR}"
    return
  fi

  # Default candidates for China Mainland deployments.
  printf '%s\n' \
    "https://registry.cn-hangzhou.aliyuncs.com" \
    "https://registry.docker-cn.com" \
    "https://mirror.ccs.tencentyun.com" \
    "https://docker.mirrors.ustc.edu.cn"
}

select_reachable_mirror() {
  local mirror
  local status

  while IFS= read -r mirror; do
    [ -n "${mirror}" ] || continue
    log "Testing Docker mirror: ${mirror}"
    status="$(curl -L -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 8 "${mirror}/v2/" || true)"
    case "${status}" in
      200|401)
        printf '%s' "${mirror}"
        return 0
        ;;
      *)
        log "Mirror not reachable: ${mirror} HTTP status: ${status:-none}"
        ;;
    esac
  done < <(docker_mirror_candidates)

  return 1
}

docker_mirror_already_exists() {
  [ -f "${DOCKER_DAEMON_JSON}" ] && grep -q '"registry-mirrors"' "${DOCKER_DAEMON_JSON}"
}

configure_docker_mirror_if_needed() {
  if docker_hub_reachable; then
    return
  fi

  log "Switching to Mirror..."

  if docker_mirror_already_exists; then
    log "Docker registry mirror already exists. Keeping current Docker configuration."
    return
  fi

  local mirror
  if ! mirror="$(select_reachable_mirror)"; then
    log "No reachable Docker mirror found. You can set DOCKER_REGISTRY_MIRROR in .env and re-run this script."
    exit 1
  fi

  "${SUDO[@]}" mkdir -p /etc/docker

  if [ -f "${DOCKER_DAEMON_JSON}" ]; then
    local backup_file
    backup_file="${DOCKER_DAEMON_JSON}.dt0013.$(date +%Y%m%d%H%M%S).bak"
    "${SUDO[@]}" cp "${DOCKER_DAEMON_JSON}" "${backup_file}"
    log "Backed up existing Docker daemon config to ${backup_file}"
  fi

  "${SUDO[@]}" tee "${DOCKER_DAEMON_JSON}" >/dev/null <<EOF
{
  "registry-mirrors": ["${mirror}"]
}
EOF

  log "Configured Docker registry mirror: ${mirror}"
  restart_docker
}

create_docker_volumes() {
  "${SUDO[@]}" docker volume create eastman-adms-mysql >/dev/null
  "${SUDO[@]}" docker volume create eastman-adms-logs >/dev/null
  "${SUDO[@]}" docker volume create eastman-adms-backup >/dev/null
}

compose_pull_with_retry() {
  cd "${PROJECT_DIR}"
  local attempt=1

  while [ "${attempt}" -le "${DOCKER_COMPOSE_PULL_RETRIES}" ]; do
    log "Retry Pull... attempt ${attempt}/${DOCKER_COMPOSE_PULL_RETRIES}"
    if "${SUDO[@]}" docker compose --env-file "${ENV_FILE}" pull mysql; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 5
  done

  log "docker compose pull failed after ${DOCKER_COMPOSE_PULL_RETRIES} attempts."
  return 1
}

start_services() {
  cd "${PROJECT_DIR}"
  compose_pull_with_retry
  "${SUDO[@]}" docker compose --env-file "${ENV_FILE}" up -d --build mysql
  "${SUDO[@]}" docker compose --env-file "${ENV_FILE}" up -d --build api
}

wait_for_mysql() {
  local attempts=60
  while [ "${attempts}" -gt 0 ]; do
    if "${SUDO[@]}" docker compose --env-file "${ENV_FILE}" exec -T mysql mysqladmin ping -h 127.0.0.1 -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" --silent >/dev/null 2>&1; then
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
  init_privilege
  detect_package_manager
  log "Detected OS: ${OS_PRETTY_NAME}"
  log "Detected package manager: ${PACKAGE_MANAGER}"
  ensure_network_tools
  ensure_project_dirs
  ensure_env_file
  load_env
  install_docker_if_missing
  install_compose_if_missing
  ensure_docker_running
  configure_docker_mirror_if_needed
  create_docker_volumes
  start_services
  wait_for_mysql
  wait_for_fastapi
  print_result
}

main "$@"
