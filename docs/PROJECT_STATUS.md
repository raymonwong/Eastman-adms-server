# Project Status

## Current Development Task

DT002

## Status

Waiting for Review

## Summary

DT002 establishes the database foundation for Eastman ADMS Server. The application checks MySQL connectivity during startup, creates required tables if they do not exist, and exposes the versioned health endpoint at `/api/v1/health`.

## Completed

- Added SQLAlchemy ORM model definitions.
- Added automatic table creation for `device`, `attendance`, `raw_request`, and `sync_log`.
- Added automatic creation of DT002 unique constraints and indexes for brand-new databases.
- Added database startup readiness logs.
- Added `GET /api/v1/health` with version `0.0.2`.
- Added `scripts/DT002_install_ubuntu.sh`.
- Removed obsolete MySQL 8.4 authentication override from Docker Compose.
- Added deployment guard for default placeholder MySQL passwords.
- Kept previous DT001 deployment scripts unchanged.
- Updated README, CHANGELOG, and deployment documentation.

## Not Included

- ADMS business logic
- ADMS protocol
- Attendance parsing
- ADMS business endpoints
- Mingdao/HAP sync
- Future DT003 features

## Next Development Task

DT003
