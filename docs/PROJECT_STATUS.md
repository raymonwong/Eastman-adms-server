# Project Status

## Current Development Task

DT005

## Status

Completed - Real Device Verified

## Summary

DT005 implements ATTLOG receive and parse from the official ZKTeco PUSH protocol V4.3 section 12.2. The server receives `POST /iclock/cdata?table=ATTLOG`, keeps the raw request, parses tab-separated attendance records, saves raw attendance events to `attendance_event`, and returns `OK:n`.

## Completed

- Added `attendance_event` as the raw ATTLOG event table.
- Added ATTLOG parser for variable-length records with 6 required fields and optional `Reserved2`, `MaskFlag`, `Temperature`, and `ConvTemperature`.
- Added V4.3 ATTLOG fields `mask_flag`, `temperature`, and `conv_temperature`.
- Added multi-line ATTLOG upload support.
- Added duplicate protection by device SN, PIN, attendance time, and verify type.
- Added `OK:n` response for ATTLOG uploads.
- Added parse-failure logging while preserving the original `raw_request`.
- Added `scripts/DT005_install_ubuntu.sh`.
- Updated deployment restart behavior so rebuilt API images are applied with a forced API container recreation.
- Added cached-image fallback for temporary Docker registry timeout during deployment.
- Verified with real device `UCE6262000016`: `raw_request.parsed=1`, response `OK:1`, and `attendance_event` records created.
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
