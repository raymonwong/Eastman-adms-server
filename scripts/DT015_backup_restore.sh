#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  echo "[DT015] $*"
}

archive="${1:-}"
confirm="${2:-}"

if [ -z "${archive}" ] || [ ! -f "${archive}" ]; then
  echo "Usage: bash scripts/DT015_backup_restore.sh /path/to/eastman-adms-backup-YYYYMMDD_HHMMSS.tar.gz [--yes]"
  exit 1
fi

cd "${PROJECT_DIR}"

if [ "${confirm}" != "--yes" ]; then
  echo "This restore imports the backup database into the configured MySQL database."
  echo "Use this on a replacement server or after confirming existing data can be overwritten."
  printf "Type RESTORE to continue: "
  read -r typed
  if [ "${typed}" != "RESTORE" ]; then
    echo "Restore cancelled."
    exit 1
  fi
fi

restore_dir="$(mktemp -d)"
trap 'rm -rf "${restore_dir}"' EXIT

log "Extracting backup"
tar -xzf "${archive}" -C "${restore_dir}"

if [ ! -f "${restore_dir}/mysql.sql" ]; then
  log "mysql.sql not found in backup package."
  exit 1
fi

if [ -f "${restore_dir}/config/.env" ]; then
  log "Restoring .env from backup package"
  [ -f ".env" ] && cp ".env" ".env.before-restore-$(date +%Y%m%d_%H%M%S)"
  cp "${restore_dir}/config/.env" ".env"
fi

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  . ".env"
  set +a
fi

: "${MYSQL_USERNAME:?MYSQL_USERNAME is required}"
: "${MYSQL_PASSWORD:?MYSQL_PASSWORD is required}"
: "${MYSQL_DATABASE:?MYSQL_DATABASE is required}"

log "Starting MySQL"
docker compose up -d mysql

log "Waiting for MySQL health"
for attempt in $(seq 1 30); do
  if docker compose exec -T mysql mysqladmin ping -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" --silent >/dev/null 2>&1; then
    break
  fi
  sleep 2
  if [ "${attempt}" = "30" ]; then
    log "MySQL is not ready."
    exit 1
  fi
done

log "Importing database backup"
docker compose exec -T mysql mysql -u"${MYSQL_USERNAME}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" < "${restore_dir}/mysql.sql"

log "Restarting ADMS services"
docker compose up -d --build

echo "========================================"
echo "Restore command completed"
echo "Please verify: http://SERVER_IP:4370/health"
echo "========================================"
