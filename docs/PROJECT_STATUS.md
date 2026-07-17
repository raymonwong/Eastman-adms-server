# Project Status

## Current Development Task

DT010.13

## Status

Waiting for Review

## Summary

DT010.13 separates Mingdao/ERP employee IDs from attendance device PIN values. `employee_id` is retained as the Mingdao reference field, while `pin` is the device user number used by future attendance device update commands. The Mingdao user API now accepts `pin` and rejects duplicate PIN ownership across different employees.

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
- Added GETREQUEST pending user sync TODO hook for DT010.2.
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
- Updated README, CHANGELOG, and project status documentation.

## Not Included

- Login
- Permission system
- Add Device
- Delete Device
- ADMS protocol changes
- API response body changes
- HTTP status changes
- ATTLOG parser changes
- OPERLOG parser changes
- USER parser changes
- Device Command Queue
- Device command processing
- User downlink
- Fingerprint synchronization
- Face synchronization
- Photo synchronization
- Attendance synchronization to Mingdao/HAP
- ERP business logic
- Attendance result calculation
- P2 language toggle
- ERP/MES/OA/WMS integrations

## Next Development Task

DT010.13 Review, then DT010.2 user command delivery
