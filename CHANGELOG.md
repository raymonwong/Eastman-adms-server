# Changelog

## Version

DT009.83

## Date

2026-07-17

## Development Task

DT009.83 Console P0 UX Logic Fixes

## Description

- Unified Console device filtering around `device_sn`; Dashboard, Latest Activity, Realtime Event Log, and Device Summary all follow the same selected device scope.
- Updated device display format to `Device Name · Device SN · Location`, with location omitted when empty.
- Added initial loading state, distinct empty state, and load failure state with a reload action.
- Added immediate loading state when switching Console device filters to avoid showing stale data.
- Added loading, empty, and load failure states to Device Management.
- Updated Console and Device Management display hierarchy so English is the primary language and Chinese is auxiliary.
- De-duplicated main ATTLOG events so a saved attendance event hides the matching raw ATTLOG row.
- Added duplicate device-name warning in Device Management and included Device Name plus SN in update success feedback.
- Added `scripts/DT009.83_install_ubuntu.sh` without overwriting previous deployment scripts.
- Kept database schema, API routes, ADMS protocol, HTTP response format, parser logic, Console layout scope, Mingdao sync, ERP logic, and attendance result calculation unchanged.

## Version

DT009.82

## Date

2026-07-16

## Development Task

DT009.82 Console V2 Data Integration

## Description

- Integrated Console V2 with real database data while keeping the DT009.81 layout unchanged.
- Limited Device Filter to All Devices plus visible devices where `show_in_console = true`.
- Updated Dashboard statistics to calculate online and offline devices from the latest Heartbeat within a 30-second window.
- Updated Latest Activity to read latest 5 ATTLOG records from `attendance_event` ordered by `attendance_time DESC`.
- Updated Realtime Event Log to return latest 10 supported events from existing raw request, ATTLOG, USER, and OPLOG data.
- Updated Device Summary status to use latest Heartbeat, and removed `show_in_console` from the JSON row payload.
- Changed unmatched device display fallback to `Unknown Device`.
- Added `scripts/DT009.82_install_ubuntu.sh` without overwriting previous deployment scripts.
- Kept database schema, Device Management, ADMS protocol, HTTP response format, parser logic, Console layout, Mingdao sync, ERP logic, and attendance result calculation unchanged.

## Version

DT009.81

## Date

2026-07-16

## Development Task

DT009.81 Console V2 Layout Refactor

## Description

- Refactored Console V2 page layout to follow the required order: operation title, server status, device filter, dashboard statistics, latest activity and realtime events, device summary.
- Converted Latest Activity from large cards into a compact 5-row table.
- Converted Realtime Event Log from large cards into a compact 10-row table with event badges and tooltips.
- Updated Device Summary into a full-width compact table and removed the redundant Show in Console column.
- Moved the global Device Filter below server status and above dashboard statistics.
- Unified Console icons with official Lucide Icons, added `package.json` with the `lucide` dependency, and avoided Wi-Fi, Signal, or Radio icons for online device status.
- Kept existing `/console` route, JSON data interface, auto-refresh, device filter behavior, database schema, Device Management, ADMS protocol, parser logic, and business logic unchanged.
- Added `scripts/DT009.81_install_ubuntu.sh` without overwriting previous deployment scripts.

## Version

DT009.8

## Date

2026-07-16

## Development Task

DT009.8 Console V2 Multi-Device Monitoring Upgrade

## Description

- Upgraded `/console` into a multi-device monitoring dashboard.
- Added global Device Filter for all devices, locations, and individual visible devices.
- Limited Console visibility to devices with `show_in_console = true`.
- Changed Console primary device display from Device SN to Device Name, keeping SN only as tooltip context.
- Added Dashboard statistics for online devices, offline devices, today's attendance, today's USER, and today's OPLOG.
- Converted Latest Activity and Realtime Event Log to follow the selected device filter.
- Added Device Summary table with location, online status, last heartbeat, last attendance, today's attendance, Record Attendance, and Show in Console.
- Added `scripts/DT009.8_install_ubuntu.sh` without overwriting previous deployment scripts.
- Kept database schema, Device Management, ADMS protocol, HTTP response format, ATTLOG parser, OPLOG parser, USER parser, Mingdao sync, ERP logic, and attendance result calculation unchanged.

## Version

DT009.7

## Date

2026-07-16

## Development Task

DT009.7 Device Management Optimization

## Description

- Changed Device Management boolean display from TRUE/FALSE to ON/OFF bilingual labels.
- Updated automatically discovered device default name to `New Machine (Device SN)`.
- Improved read-only styling for Device SN, Created Time, and Updated Time.
- Improved switch alignment and consistent switch labels.
- Added confirmation when disabling Record Attendance, with optional automatic Show in Console disable.
- Added `scripts/DT009.7_install_ubuntu.sh` without overwriting previous deployment scripts.
- Kept database schema, API paths, Console behavior, ADMS protocol, Mingdao sync, ERP logic, and attendance result calculation unchanged.

## Version

DT009.6

## Date

2026-07-16

## Development Task

DT009.6 Device Management Module Phase 1

## Description

- Added Device Management configuration page at `/dms`.
- Added `GET /api/devices`, `GET /api/device/{sn}`, and `PUT /api/device/{sn}`.
- Added device configuration fields: `location`, `record_attendance`, and `show_in_console`.
- Updated automatic device registration to default new devices to `New Machine`, `record_attendance = true`, and `show_in_console = true`.
- Added ATTLOG recording control: when `record_attendance = false`, ATTLOG is received normally but attendance events are not saved.
- Kept Console behavior, ADMS protocol, HTTP response format, USER parser, OPLOG parser, Mingdao sync, ERP logic, and attendance result calculation unchanged.
- Added `scripts/DT009.6_install_ubuntu.sh` without overwriting previous deployment scripts.

## Version

DT009.5

## Date

2026-07-16

## Development Task

DT009.5 ADMS Server Console

## Description

- Added `/console` as the single ADMS Server development console entry.
- Added dark-theme Jinja2 and Bootstrap console page with Chinese and English labels.
- Added server status, database status, API status, and server time display.
- Added multi-device status cards with Online and Offline states based on Last Seen.
- Added Last Seen, Last Heartbeat, Last Data Upload, Last Raw Request ID, Last Request Type, last ATTLOG, last OPERLOG, last USER sync, client IP, and push version display.
- Set Console Online/Offline display to use the latest device request within a 60-second window instead of heartbeat-only checks.
- Added realtime event log based on existing raw request and parser result tables.
- Added today's Heartbeat, ATTLOG, OPERLOG, and USER counters.
- Added latest attendance activity panel.
- Added 2-second auto refresh, manual Refresh, and browser-only Clear Event Log.
- Optimized Console layout into a compact, high-density desktop operations view.
- Reworked Current State into a responsive 4/2/1 information grid.
- Reworked Device Status into a 3/2/1 responsive device-card grid.
- Reworked Realtime Event Log to use compact rows and internal scrolling.
- Added `scripts/DT009.5_install_ubuntu.sh` without overwriting previous deployment scripts.
- Kept database schema, ADMS protocol, API response bodies, HTTP status codes, ATTLOG parser, OPERLOG parser, USER parser, Mingdao sync, ERP logic, and attendance result calculation unchanged.

## Version

DT009

## Date

2026-07-16

## Development Task

DT009 ADMS Debug Log

## Description

- Added unified ADMS debug log output for development troubleshooting.
- Added `HANDSHAKE` logs for initialization requests.
- Added `HEARTBEAT` logs for every `GET /iclock/getrequest`.
- Added `ATTLOG RECEIVED` and `ATTLOG SAVED` logs.
- Added `OPERLOG RECEIVED` and `OPERLOG SAVED` logs.
- Added `USER RECEIVED` and `USER SAVED` logs.
- Standardized parser exception logs as `ERROR`.
- Added `scripts/DT009_install_ubuntu.sh` without overwriting previous deployment scripts.
- Kept database schema, API routes, HTTP status codes, response bodies, parsers, raw request persistence, Mingdao sync, ERP logic, and attendance result calculation unchanged.

## Version

DT008

## Date

2026-07-12

## Development Task

DT008 USER Receive and Parse as OPERLOG Extension

## Description

- Added `device_user` table for USER records uploaded inside `table=OPERLOG` request bodies.
- Added unique constraint on `device_sn` and `pin`.
- Added USER parser for fields `PIN`, `Name`, `Pri`, `Passwd`, `Card`, `Grp`, `TZ`, `Verify`, `ViceCard`, `StartDatetime`, and `EndDatetime`.
- Added device-user upsert behavior when the same device uploads the same PIN again.
- Extended OPERLOG parser dispatch so `OPLOG` continues to save `operation_event` and `USER` saves `device_user`.
- Added `OK:n` response support for USER records inside OPERLOG uploads.
- Added `scripts/DT008_install_ubuntu.sh` without overwriting previous deployment scripts.
- Kept raw request persistence, ATTLOG, OPLOG, device sync state, user downlink, Command Queue, Mingdao sync, ERP logic, and attendance result calculation unchanged.

## Version

DT006 Review Fix

## Date

2026-07-12

## Development Task

DT006 OPERLOG Real Device Parser Compatibility

## Description

- Updated OPERLOG parser to accept real device records that start with `OPLOG` and use space-separated fields.
- Kept tab-separated PUSH protocol records compatible.
- Added variable-length optional field handling so one valid OPLOG line creates one `operation_event` record.
- Updated DT006 deployment parser verification to use the verified real device format.
- Kept `raw_request`, ATTLOG, device sync state, Command Queue, Mingdao sync, ERP logic, and future business logic unchanged.

## Version

DT007

## Date

2026-07-12

## Development Task

DT007 Device Sync State

## Description

- Added `device_sync_state` table for per-device data sync state.
- Added unique constraint on `device_sn` and `data_type`.
- Added supported sync data types for `ATTLOG`, `OPERLOG`, `USER`, `FINGER`, `FACE`, and `PHOTO`.
- Added sync state update after successful ATTLOG parsing.
- Added sync state update after successful OPERLOG parsing.
- Added sync state update logs with device SN, data type, device stamp, and raw request ID.
- Kept initialization response fixed at `ATTLOGStamp=9999` and `OPERLOGStamp=9999`.
- Added `scripts/DT007_install_ubuntu.sh` without overwriting previous deployment scripts.
- Kept dynamic Stamp responses, USER, FACE, FINGER, Command Queue, Mingdao sync, ERP logic, and attendance result calculation out of DT007.

## Version

DT006

## Date

2026-07-10

## Development Task

DT006 OPERLOG Receive and Parse

## Description

- Added `operation_event` table for raw OPERLOG operation events.
- Added OPERLOG parsing for `POST /iclock/cdata?table=OPERLOG` according to PUSH protocol V4.3 section 12.4.
- Saved multi-line OPERLOG uploads as individual raw operation events.
- Added `operation_code` and `operation_name` while preserving the original operation code.
- Added `OK:n` response for OPERLOG uploads.
- Kept `raw_request` persistence before parsing and updated the stored response to `OK:n`.
- Added parse-failure logging without aborting later records in the same upload.
- Added `scripts/DT006_install_ubuntu.sh` without overwriting previous deployment scripts.
- Kept USER, FACE, FINGER, BIODATA, command queue, Mingdao sync, ERP logic, and attendance result calculation out of DT006.

## Eastman ADMS Server V1.0

Completed:

- DT001 Environment
- DT002 Database
- DT003 Device Connection
- DT004 Initialization Handshake
- DT005 ATTLOG Protocol Parser

Verified:

- Official Push Protocol V2.4.2
- Real Device Connected
- ATTLOG Parsing
- attendance_event
- raw_request

## Version

DT005

## Date

2026-07-10

## Development Task

DT005 ATTLOG Receive and Parse

## Description

- Added `attendance_event` table for raw ATTLOG attendance events.
- Added ATTLOG parsing for `POST /iclock/cdata?table=ATTLOG` according to PUSH protocol V4.3 section 12.2.
- Saved multi-line ATTLOG uploads as individual raw attendance events.
- Added V4.3 ATTLOG fields `mask_flag`, `temperature`, and `conv_temperature` while keeping 7-field device compatibility.
- Added variable-length ATTLOG compatibility for real devices that omit optional fields after `Reserved1`.
- Added duplicate protection by device SN, PIN, attendance time, and verify type.
- Kept `raw_request` persistence before parsing and updated the stored response to `OK:n`.
- Added parse-failure logging without aborting later records in the same upload.
- Added `scripts/DT005_install_ubuntu.sh` without overwriting previous deployment scripts.
- Updated deployment restart behavior to force recreate the API container after rebuilding the project image.
- Added cached-image fallback when registry pulls time out but required Docker images already exist locally.
- Verified real device ATTLOG upload with `raw_request.parsed=1`, `OK:1` response, and `attendance_event` insertion.
- Removed temporary ATTLOG debug instrumentation after real-device verification.
- Kept ERP logic, attendance result calculation, Mingdao sync, user sync, and command queue out of DT005.

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
