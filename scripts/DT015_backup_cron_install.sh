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

  ADMS_BACKUP_TIME="$(get_setting ADMS_BACKUP_TIME "${ADMS_BACKUP_TIME:-03:30}")"
  if ! [[ "${ADMS_BACKUP_TIME}" =~ ^[0-9]{2}:[0-9]{2}$ ]]; then
    log "Invalid ADMS_BACKUP_TIME: ${ADMS_BACKUP_TIME}"
    exit 1
  fi

  hour="${ADMS_BACKUP_TIME%:*}"
  minute="${ADMS_BACKUP_TIME#*:}"
  hour="$((10#${hour}))"
  minute="$((10#${minute}))"
  if [ "${hour}" -gt 23 ] || [ "${minute}" -gt 59 ]; then
    log "Invalid ADMS_BACKUP_TIME: ${ADMS_BACKUP_TIME}"
    exit 1
  fi

  mkdir -p logs
  tmp_file="$(mktemp)"
  trap 'rm -f "${tmp_file}"' EXIT

  crontab -l 2>/dev/null | sed '/# ADMS DT015 backup begin/,/# ADMS DT015 backup end/d' > "${tmp_file}" || true
  {
    echo "# ADMS DT015 backup begin"
    echo "${minute} ${hour} * * * cd ${PROJECT_DIR} && . ./.env && [ \"\${ADMS_BACKUP_ENABLED:-true}\" = \"true\" ] && bash scripts/DT015_backup_create.sh >> logs/backup_cron.log 2>&1"
    echo "# ADMS DT015 backup end"
  } >> "${tmp_file}"
  crontab "${tmp_file}"

  echo "========================================"
  echo "ADMS daily backup cron installed"
  echo "Time: ${ADMS_BACKUP_TIME} Dubai server time"
  echo "Log: ${PROJECT_DIR}/logs/backup_cron.log"
  echo "========================================"
}

main "$@"
