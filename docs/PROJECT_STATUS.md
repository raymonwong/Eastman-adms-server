# Project Status

## Current Development Task

DT009.83

## Status

Waiting for Review

## Summary

DT009.83 completes the Console P0 UX logic fixes. Device filtering, device identity display, loading states, and ATTLOG main-log de-duplication were improved while keeping the existing `/console` route, Device Management module, database schema, ADMS protocol, and parser behavior unchanged.

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
- Updated Latest Activity to show latest 5 ATTLOG records by attendance time.
- Updated Realtime Event Log to show latest 10 supported protocol events.
- Updated Device Summary to use latest Heartbeat for Online/Offline status and real attendance counts.
- Added `scripts/DT009.82_install_ubuntu.sh`.
- Unified Console device filtering by `device_sn` across Dashboard, Latest Activity, Realtime Event Log, and Device Summary.
- Updated device display format to include Device Name, Device SN, and Location.
- Added loading, empty, and load failure states to the Console page.
- De-duplicated ATTLOG main log rows when the corresponding saved attendance event is shown.
- Added duplicate device-name warning and Device Name plus SN update feedback in Device Management.
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
- P1 realtime event-log restructuring
- P1 business-language event mapping
- P1 advanced edit-modal workflow
- P1 switch impact explanations
- P2 navigation restructuring
- P2 exception-priority view
- P2 language toggle

## Next Development Task

DT009.83 Review, then DT009.83 P1
