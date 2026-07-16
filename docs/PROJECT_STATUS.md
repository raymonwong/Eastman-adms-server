# Project Status

## Current Development Task

DT009.83

## Status

Waiting for Review

## Summary

DT009.83 completes the Console P0/P1/P2 UX improvements. Device filtering, device identity display, loading states, ATTLOG main-log de-duplication, event-log controls, business-language event labels, Device Management edit safety, exception-priority monitoring, and Device Summary search/filter/sort were improved while keeping the existing `/console` route, database schema, ADMS protocol, and parser behavior unchanged.

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
- Personnel synchronization
- Mingdao/HAP sync
- ERP business logic
- Attendance result calculation
- P2 language toggle

## Next Development Task

DT009.83 Review
