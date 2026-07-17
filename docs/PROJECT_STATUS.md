# Project Status

## Current Development Task

DT013.1 Mingdao Attendance Integration Configuration

## Status

Implemented - Waiting for Review

## Summary

DT013.1 splits Communication Console -> System Settings into two sub pages. `/settings/integration` is the Inbound API page for Mingdao pushing employee data into ADMS. `/settings/attendance-sync` is the Attendance Synchronization page for configuring the OpenAPI URL, AppKey, Sign, Worksheet ID, and field mappings needed by future DT014 Attendance Synchronization. It does not upload attendance records.

## Completed

- Added `/dms` as the independent Device Management page.
- Added bilingual device list and edit UI.
- Added `GET /api/devices`.
- Added `GET /api/device/{sn}`.
- Added `PUT /api/device/{sn}` for `device_name`, `location`, `record_attendance`, and `show_in_console`.
- Added `location`, `record_attendance`, and `show_in_console` fields to the existing `device` table.
- Updated automatic device registration default values.
- Added ATTLOG save skip behavior when `record_attendance = false`.
- Added `scripts/DT009.6_install_ubuntu.sh`.
- Added `scripts/DT009.7_install_ubuntu.sh`.
- Optimized boolean display to `ON / 开启` and `OFF / 关闭`.
- Updated default auto-discovered device names to `New Machine (Device SN)`.
- Improved visual read-only treatment for Device SN, Created Time, and Updated Time.
- Added confirmation when Record Attendance is turned off.
- Added Console V2 global Device Filter.
- Limited Console data to devices with `show_in_console = true`.
- Added Dashboard statistics for online devices, offline devices, today's attendance, today's USER, and today's OPLOG.
- Added filtered Latest Activity and Realtime Event Log.
- Added Device Summary table.
- Changed Console primary display from Device SN to Device Name.
- Added `scripts/DT009.8_install_ubuntu.sh`.
- Refactored Console V2 layout into the required order: server status, device filter, dashboard, latest activity and realtime event tables, and device summary.
- Converted Latest Activity to a compact 5-row table.
- Converted Realtime Event Log to a compact 10-row table.
- Removed redundant Show in Console from Device Summary.
- Unified Console icons with official Lucide Icons, added `package.json` with the `lucide` dependency, and avoided Wi-Fi-style online icons.
- Added `scripts/DT009.81_install_ubuntu.sh`.
- Integrated Device Filter with visible devices from the `device` table.
- Updated Dashboard to use real online/offline, ATTLOG, USER, and OPLOG counts.
- Updated Latest Activity to show ATTLOG records by attendance time.
- Updated Realtime Event Log to show latest 10 supported protocol events.
- Updated Device Summary to use latest Heartbeat for Online/Offline status and real attendance counts.
- Added `scripts/DT009.82_install_ubuntu.sh`.
- Unified Console device filtering by `device_sn` across Dashboard, Latest Activity, Realtime Event Log, and Device Summary.
- Updated device display format to include Device Name, Device SN, and Location.
- Added loading, empty, and load failure states to the Console page.
- Added immediate Console loading state when switching device filters.
- Added loading, empty, and load failure states to Device Management.
- Updated Console and Device Management display hierarchy so English is primary and Chinese is auxiliary.
- De-duplicated ATTLOG main log rows when the corresponding saved attendance event is shown.
- Added duplicate device-name warning and Device Name plus SN update feedback in Device Management.
- Added event type filtering, keyword search, pause/resume refresh, auto-scroll toggle, clear filters, heartbeat summary, and current-page log clear confirmation.
- Added temporary red flashing for newly arrived Latest Activity and Realtime Event Log rows, returning to the normal background after the notification flash.
- Converted protocol codes to business-language labels while preserving raw technical details in collapsible rows with copy support.
- Added synthetic Device Online and Device Offline monitor events based on current heartbeat status.
- Added Device Management dirty-state detection, disabled Save when unchanged, saving state, unsaved-change prompt, inline validation, switch impact descriptions, and detailed save failures.
- Reworked Console navigation into Operation Monitor and Device Management, with Protocol Console and System Settings marked as under development.
- Added Exception Priority cards for offline devices, heartbeat timeout devices, latest exception time, and latest normal attendance.
- Added Device Summary status filter, keyword search, and sorting by last heartbeat, last attendance, and today's attendance.
- Added full Latest Activity attendance-time display, 5-digit display formatting for employee PIN values, and expanded Latest Activity to 7 rows.
- Changed Console online/offline timeout to 60 seconds.
- Ensured Realtime Event Log keeps the latest event at the top after filtering.
- Added `scripts/DT009.83_install_ubuntu.sh`.
- Added `POST /api/v1/users`.
- Added `POST /api/v1/users/batch`.
- Added `GET /api/v1/users`.
- Added `GET /api/v1/users/{employee_id}`.
- Protected all Mingdao user APIs with `MINGDAO_API_TOKEN`, supporting `Authorization: Bearer <token>` and `X-API-Key`.
- Added text trimming, supported privilege validation, and a 500-user maximum batch limit.
- Extended `device_user` with `employee_id`, `department`, `card_no`, and `enabled`.
- Added device-side USER upload metadata fields to `device_user`: `last_device_sn`, `last_device_user_upload_at`, and `last_device_raw_request_id`.
- Added `device_user_sync` with `PENDING`, `SYNCING`, `SYNCED`, and `FAILED` status support.
- Added `device_user_sync` foreign keys and status validation constraints.
- Added idempotent UPSERT behavior by `employee_id`.
- Added per-device user sync record creation when a Mingdao user changes.
- Added GETREQUEST pending user sync hook for future command delivery.
- Added Console user sync event display and separated device USER upload statistics from Mingdao user synchronization statistics.
- Added `scripts/DT010.1_install_ubuntu.sh`.
- Added `/settings/integration` under Communication Console System Settings.
- Added Mingdao Integration runtime display for current API URL, masked API token, server time, API status, authentication status, last API request time, and caller IP.
- Added API token Show, Hide, Copy, Generate New Token, and Save controls.
- Added Integration Health Check UI and endpoint.
- Added generated cURL example for the current API URL.
- Added permanent Integration Guide in the Console page.
- Added `docs/Mingdao_API_Integration.md`.
- Added `scripts/DT010.11_install_ubuntu.sh`.
- Enhanced Integration page so the API token is masked by default and only shown through the Show action.
- Added Mingdao Configuration Guide section directly on the Integration page.
- Added Copy Mingdao Configuration action.
- Added API Test form for `POST /api/v1/users`.
- Added runtime statistics for last API response code and total API request count.
- Added Open Integration Documentation action.
- Added explicit `pin` support to Mingdao user API requests and responses.
- Kept `employee_id` as Mingdao/ERP reference data and `pin` as the future attendance-device update field.
- Added duplicate PIN ownership protection with HTTP `409 Conflict`.
- Updated `/settings/integration` examples, cURL output, API Test form, README, and Mingdao integration documentation to show `employee_id` and `pin` separately.
- Added `scripts/DT010.13_install_ubuntu.sh`.
- Added `/users` as the read-only ADMS Users Console page.
- Added `/api/adms-users` as the read-only ADMS user list endpoint.
- Grouped ADMS users by department and displayed employee ID, device PIN, source, card number, privilege, enabled status, sync counts, last device upload, and updated time.
- Added ADMS Users navigation from Operation Monitor, System Settings Integration, and Device Management.
- Added `scripts/DT010.14_install_ubuntu.sh`.
- Added `/iclock/getrequest` user command delivery with `C:<sync_id>:DATA UPDATE USERINFO ...`.
- Added `/iclock/devicecmd` ACK parsing for user synchronization.
- Added `device_user_sync` transitions from `PENDING` to `SYNCING`, then `SYNCED` or `FAILED`.
- Added bounded retry configuration with `USER_SYNC_MAX_RETRY` and `USER_SYNC_ACK_TIMEOUT_SECONDS`.
- Added DT011 user sync events: `USER CREATE`, `USER UPDATE`, `USER DISABLE`, `USER SYNC START`, `USER SYNC SUCCESS`, `USER SYNC FAILED`, `USER RETRY`, and `USER ACK RECEIVED`.
- Added per-device sync detail display in `/users`.
- Added `scripts/DT011_install_ubuntu.sh`.
- Limited Mingdao user sync generation and GETREQUEST delivery to devices with `record_attendance = true`.
- Added automatic sync rebuild when a device changes from `record_attendance = false` to `true`.
- Added automatic sync cleanup when a device changes from `record_attendance = true` to `false`.
- Removed the Card No column from the ADMS Users Console.
- Added `scripts/DT011.1_install_ubuntu.sh`.
- Added `employee_record_id` to `device_user`.
- Required `employee_record_id` in `POST /api/v1/users` and `POST /api/v1/users/batch`.
- Updated UPSERT behavior so existing users refresh `employee_record_id`.
- Added `employee_record_id` to Mingdao User API responses and `/api/adms-users`.
- Added Employee Record ID display and search support to `/users`.
- Updated `/settings/integration` guide, cURL output, API Test form, and documentation examples.
- Added `scripts/DT010.12_install_ubuntu.sh`.
- Split System Settings into `/settings/integration` for Inbound API and `/settings/attendance-sync` for Attendance Synchronization.
- Added Attendance Synchronization configuration page.
- Added configurable Mingdao Attendance OpenAPI URL, AppKey, Sign, Worksheet ID, and fixed ADMS-to-Mingdao field mapping targets.
- Added read-only Test Connection for Mingdao worksheet metadata and configured field ID verification.
- Added Attendance Synchronization summary including status, API URL, Worksheet ID, token status, configured fields, last test time, and last test result.
- Added DT014 duplicate-prevention design based on `attendance_event.id` as the local idempotency key.
- Added `scripts/DT013.1_install_ubuntu.sh`.
- Updated README, CHANGELOG, and project status documentation.

## Not Included

- Login
- Permission system
- Add Device
- Delete Device
- Fingerprint synchronization
- Face synchronization
- Photo synchronization
- Password synchronization
- User delete command
- ATTLOG parser changes
- OPERLOG parser changes
- USER parser changes
- Attendance synchronization to Mingdao/HAP
- ERP business logic
- Attendance result calculation
- P2 language toggle
- ERP/MES/OA/WMS integrations

## Next Development Task

DT011.1 Review, then DT012 fingerprint synchronization planning
