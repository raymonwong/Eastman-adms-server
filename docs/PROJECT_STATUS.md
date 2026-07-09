# Project Status

## Current Development Task

DT001.4

## Status

Waiting for Review

## Summary

DT001.4 completes the DT001 deployment path for the verified production server. Alibaba Cloud Linux 3 remains the primary deployment target. Docker and Docker Compose are verified before deployment, and all Docker images are configured through `.env` with DaoCloud Proxy defaults.

## Completed

- Added `scripts/DT001.4_install_ubuntu.sh`.
- Changed MySQL image configuration to `MYSQL_IMAGE`.
- Changed Python base image configuration to `PYTHON_IMAGE`.
- Changed API image tag configuration to `API_IMAGE`.
- Added DaoCloud Proxy defaults for production deployment.
- Added idempotent `.env` completion for existing DT001 deployments.
- Removed Docker Registry Mirror configuration from the DT001.4 install flow.
- Added `docker compose ps` and `docker ps` verification output.
- Kept previous DT001, DT001.2, and DT001.3 scripts unchanged.
- Updated README, CHANGELOG, and deployment documentation.

## Not Included

- ADMS business logic
- API business endpoints
- Database schema
- Mingdao/HAP sync
- Future DT002 features

## Next Development Task

DT002
