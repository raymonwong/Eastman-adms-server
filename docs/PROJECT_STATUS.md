# Project Status

## Current Development Task

DT009.8

## Status

Waiting for Review

## Summary

DT009.8 upgrades `/console` into Console V2, a multi-device monitoring center. Device Management remains the configuration module, while Console only displays runtime monitoring data.

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

## Next Development Task

DT010
