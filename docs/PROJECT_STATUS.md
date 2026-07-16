# Project Status

## Current Development Task

DT009.6

## Status

Waiting for Review

## Summary

DT009.6 adds the Device Management module at `/dms`. The module is independent from Console and only handles device configuration, including device name, location, attendance recording control, and the stored show-in-console flag.

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
- Updated README, CHANGELOG, and project status documentation.

## Not Included

- Login
- Permission system
- Add Device
- Delete Device
- Console filtering by `show_in_console`
- Console device name display
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
