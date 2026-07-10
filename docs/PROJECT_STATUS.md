# Project Status

## Current Development Task

DT005

## Status

Waiting for Review

## Summary

DT005 implements ATTLOG receive and parse from the official ZKTeco PUSH protocol V4.3 section 12.2. The server receives `POST /iclock/cdata?table=ATTLOG`, keeps the raw request, parses tab-separated attendance records, saves raw attendance events to `attendance_event`, and returns `OK:n`.

## Completed

- Added `attendance_event` as the raw ATTLOG event table.
- Added ATTLOG parser for both 7-field legacy records and 10-field V4.3 records.
- Added V4.3 ATTLOG fields `mask_flag`, `temperature`, and `conv_temperature`.
- Added multi-line ATTLOG upload support.
- Added duplicate protection by device SN, PIN, attendance time, and verify type.
- Added `OK:n` response for ATTLOG uploads.
- Added parse-failure logging while preserving the original `raw_request`.
- Added `scripts/DT005_install_ubuntu.sh`.
- Kept DT004 initialization handshake, `getrequest`, `devicecmd`, `OPERLOG`, and `options` compatibility untouched.
- Updated README, CHANGELOG, and project status documentation.

## Not Included

- ADMS business logic
- Attendance result calculation
- Scheduling
- Late/early/overtime/leave/makeup-card logic
- Payroll
- Statistics
- User synchronization
- Device commands
- Command Queue
- Mingdao/HAP sync
- Future DT006 features

## Next Development Task

DT006
