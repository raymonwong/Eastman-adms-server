# Changelog

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
