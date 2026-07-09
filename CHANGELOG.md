# Changelog

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
