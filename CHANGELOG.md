# Changelog

## Version

DT004

## Date

2026-07-10

## Development Task

DT004 Initialization Handshake

## Description

- Added official `GET OPTION FROM:` response for `GET /iclock/cdata?options=all`.
- Added default initialization values for `ATTLOGStamp`, `OPERLOGStamp`, `ATTPHOTOStamp`, `ERRORLOGStamp`, `Delay`, `ErrorDelay`, `Realtime`, `TransInterval`, `TransTimes`, `TransFlag`, `TimeZone`, `PushProtVer`, `PushOptionsFlag`, `PushOptions`, and `ServerVer`.
- Set Dubai timezone response to `TimeZone=4`.
- Added device handshake metadata fields for push version, device type, language, push options, and last handshake time.
- Added concise initialization completion logs.
- Added `scripts/DT004_install_ubuntu.sh` without overwriting previous deployment scripts.
- Kept ATTLOG parsing, user synchronization, and command queue out of DT004.

## Version

DT003

## Date

2026-07-09

## Development Task

DT003 ADMS Device Connection Phase 1

## Description

- Added `GET /iclock/cdata` and `POST /iclock/cdata` for first-stage ADMS device connection.
- Saved complete raw HTTP request snapshots to `raw_request`.
- Added `parsed` and `request_hash` fields for future parsing and duplicate detection.
- Added raw request fields for URL, query parameters, client IP, User-Agent, Content-Type, response body, response status code, request size, and response size.
- Added `device_event_log` for device connection event history.
- Added automatic device registration and online timestamp updates from request `SN`.
- Added concise connection logs for device connection verification.
- Added device-side ADMS configuration and troubleshooting notes.
- Kept the task limited to 100% receive and 0% parse.

## Version

DT002

## Date

2026-07-09

## Development Task

DT002 Database Foundation

## Description

- Added SQLAlchemy ORM models for `device`, `attendance`, `raw_request`, and `sync_log`.
- Added startup database connection check and idempotent table creation.
- Added required startup log output for database readiness.
- Added `GET /api/v1/health` returning project, version, status, database, and time.
- Added `scripts/DT002_install_ubuntu.sh` without overwriting previous deployment scripts.
- Updated default API image tag to stable `eastman-adms-server:latest`.
- Removed obsolete MySQL authentication override for MySQL 8.4.
- Added explicit unique constraint for `device.device_sn`.
- Added targeted indexes for future ADMS query paths on `attendance` and `raw_request`.
- Changed DT002 development deployment to warn, not stop, when MySQL password is still a placeholder.
- Refactored DT002 deployment to run `docker compose build --pull` before `docker compose up -d`.
- Added `SHOW TABLES;` verification for `device`, `attendance`, `raw_request`, and `sync_log`.
- Added failure diagnostics for Compose status, Docker status, and recent MySQL/API logs.
- Added optional `--reset-db` mode for development database recreation.
- Kept the task limited to database architecture only.

## Version

DT001.4

## Date

2026-07-09

## Development Task

DT001 Deployment Completion Fix

## Description

- Added `scripts/DT001.4_install_ubuntu.sh` without overwriting previous deployment scripts.
- Changed Docker images to come from `.env` instead of hardcoded Compose values.
- Added DaoCloud Proxy defaults for MySQL 8.4 and Python 3.12 images.
- Added idempotent `.env` completion for DT001.4 image variables.
- Removed Docker Registry Mirror configuration from the DT001.4 deployment flow.
- Added explicit image pull failure output for MySQL and Python images.
- Added runtime verification with `docker compose ps` and `docker ps`.
- Kept the fix limited to DT001 deployment completion only.

## Version

DT001.3

## Date

2026-07-09

## Development Task

DT001 Deployment Review Fix

## Description

- Added `scripts/DT001.3_install_ubuntu.sh` without overwriting previous deployment scripts.
- Added Docker Hub reachability detection for China Mainland deployments.
- Added Docker registry mirror configuration when Docker Hub is unreachable.
- Added built-in mirror candidates for Aliyun, Docker Official China if available, Tencent, and USTC.
- Added user-configurable `DOCKER_REGISTRY_MIRROR` in `.env.example`.
- Added Docker restart after mirror configuration.
- Added `docker compose pull` retry logic with at least 3 attempts.
- Kept the fix limited to deployment reliability only.

## Version

DT001.2

## Date

2026-07-09

## Development Task

DT001 Deployment Review Fix

## Description

- Added `scripts/DT001.2_install_ubuntu.sh` without overwriting the previous DT001 installer.
- Defined Alibaba Cloud Linux 3 as the primary deployment target.
- Added compatibility support for Ubuntu 22.04+, Ubuntu 24.04+, and RHEL compatible distributions.
- Added `/etc/os-release` based OS detection with `ID` and `ID_LIKE` handling.
- Added package manager detection for `apt`, `dnf`, and `yum`.
- Added Docker CE repository handling for Alibaba Cloud Linux 3 and RHEL compatible distributions.
- Kept the fix limited to deployment compatibility only.

## Version

DT001.1

## Date

2026-07-09

## Development Task

DT001 Review

## Description

- Unified project naming to `eastman-adms-server`.
- Renamed Docker volumes to `eastman-adms-mysql`, `eastman-adms-logs`, and `eastman-adms-backup`.
- Renamed Ubuntu installer to `scripts/DT001_install_ubuntu.sh`.
- Added `docs/Architecture.md` and `docs/Deploy.md`.
- Expanded `.env.example` with the required initialization configuration fields.
- Reworked README structure for project intro, requirements, quick deploy, directory layout, Docker services, next stage, and license placeholder.
- Kept DT001.1 limited to initialization quality fixes only.

## Version

DT001

## Date

2026-07-09

## Development Task

DT001

## Description

- Initialized `eastman-adms-server` project structure.
- Added Docker Compose deployment for FastAPI and MySQL 8.
- Added Python 3.12 FastAPI application with SQLAlchemy database connectivity check.
- Added `.env.example` configuration template.
- Added idempotent Ubuntu installer.
- Added Docker volumes for MySQL, logs, and backup storage.
