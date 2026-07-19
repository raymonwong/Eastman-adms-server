#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  echo "[DT015] $*"
}

main() {
  cd "${PROJECT_DIR}"

  if [ -f ".env" ]; then
    set -a
    # shellcheck disable=SC1091
    . ".env"
    set +a
  fi

  : "${MYSQL_USERNAME:?MYSQL_USERNAME is required}"
  : "${MYSQL_PASSWORD:?MYSQL_PASSWORD is required}"
  : "${MYSQL_DATABASE:?MYSQL_DATABASE is required}"

  get_setting() {
    local key="$1"
    local fallback="$2"
    local value
    value="$(docker compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" -N -s -e "SELECT setting_value FROM integration_setting WHERE setting_key='${key}' LIMIT 1;" 2>/dev/null || true)"
    if [ -n "${value}" ]; then
      echo "${value}"
    else
      echo "${fallback}"
    fi
  }

  ADMS_BACKUP_RETENTION_COUNT="$(get_setting ADMS_BACKUP_RETENTION_COUNT "${ADMS_BACKUP_RETENTION_COUNT:-14}")"
  ADMS_BACKUP_HOST_DIR="$(get_setting ADMS_BACKUP_HOST_DIR "${ADMS_BACKUP_HOST_DIR:-${PROJECT_DIR}/backups}")"
  ADMS_BACKUP_CONTAINER_DIR="$(get_setting ADMS_BACKUP_CONTAINER_DIR "${ADMS_BACKUP_CONTAINER_DIR:-/app/backup}")"

  mkdir -p "${ADMS_BACKUP_HOST_DIR}" logs
  work_dir="$(mktemp -d "${ADMS_BACKUP_HOST_DIR}/.dt015.XXXXXX")"
  stamp="$(date +%Y%m%d_%H%M%S)"
  archive="${ADMS_BACKUP_HOST_DIR}/eastman-adms-backup-${stamp}.tar.gz"

  cleanup() {
    rm -rf "${work_dir}"
  }
  trap cleanup EXIT

  log "Creating MySQL dump"
  docker compose exec -T mysql mysqldump \
    -u"${MYSQL_USERNAME}" \
    -p"${MYSQL_PASSWORD}" \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    "${MYSQL_DATABASE}" > "${work_dir}/mysql.sql"

  mkdir -p "${work_dir}/config" "${work_dir}/project"
  [ -f ".env" ] && cp ".env" "${work_dir}/config/.env"
  [ -f "docker-compose.yml" ] && cp "docker-compose.yml" "${work_dir}/project/docker-compose.yml"
  [ -f "Dockerfile" ] && cp "Dockerfile" "${work_dir}/project/Dockerfile"
  [ -f "app/requirements.txt" ] && cp "app/requirements.txt" "${work_dir}/project/requirements.txt"
  [ -f "docs/Backup_and_Restore.md" ] && cp "docs/Backup_and_Restore.md" "${work_dir}/README_RESTORE.txt"

  {
    echo "project=eastman-adms-server"
    echo "created_at=$(date '+%Y-%m-%d %H:%M:%S %z')"
    echo "git_head=$(git rev-parse HEAD 2>/dev/null || echo unknown)"
    echo "mysql_database=${MYSQL_DATABASE}"
  } > "${work_dir}/metadata.txt"

  log "Packing backup archive"
  tar -C "${work_dir}" -czf "${archive}" .

  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${archive}" > "${archive}.sha256"
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "${archive}" > "${archive}.sha256"
  fi

  log "Copying archive to API container download directory"
  if docker compose ps -q api >/dev/null 2>&1; then
    docker compose exec -T api mkdir -p "${ADMS_BACKUP_CONTAINER_DIR}" || true
    docker cp "${archive}" "eastman-adms-api:${ADMS_BACKUP_CONTAINER_DIR}/" || true
    [ -f "${archive}.sha256" ] && docker cp "${archive}.sha256" "eastman-adms-api:${ADMS_BACKUP_CONTAINER_DIR}/" || true
  fi

  log "Applying retention policy: keep ${ADMS_BACKUP_RETENTION_COUNT} packages"
  ls -1t "${ADMS_BACKUP_HOST_DIR}"/eastman-adms-backup-*.tar.gz 2>/dev/null \
    | tail -n +"$((ADMS_BACKUP_RETENTION_COUNT + 1))" \
    | xargs -r rm -f

  if docker compose ps -q api >/dev/null 2>&1; then
    docker compose exec -T api sh -c "ls -1t '${ADMS_BACKUP_CONTAINER_DIR}'/eastman-adms-backup-*.tar.gz 2>/dev/null | tail -n +$((ADMS_BACKUP_RETENTION_COUNT + 1)) | xargs -r rm -f" || true
  fi

  echo "========================================"
  echo "Backup Ready"
  echo "Host file: ${archive}"
  echo "Console: /settings/backup"
  echo "========================================"
}

main "$@"
