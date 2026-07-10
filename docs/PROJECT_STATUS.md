# Project Status

## Current Development Task

DT006

## Status

Waiting for Review

## Summary

DT006 implements OPERLOG receive and parse from the official ZKTeco PUSH protocol V4.3 section 12.4. The server receives `POST /iclock/cdata?table=OPERLOG`, keeps the raw request, parses tab-separated operation records, saves raw operation events to `operation_event`, and returns `OK:n`.

## Completed

- Added `operation_event` as the raw OPERLOG event table.
- Added OPERLOG parser for `OPLOG`, `OpType`, `Operator`, `OpTime`, `OpWho`, `Value1`, `Value2`, and `Value3`.
- Added operation code and operation name storage while preserving the original operation code.
- Added multi-line OPERLOG upload support.
- Added `OK:n` response for OPERLOG uploads.
- Added parse-failure logging while preserving the original `raw_request`.
- Added `scripts/DT006_install_ubuntu.sh`.
- Kept DT001, DT002, DT003, DT004, and DT005 compatibility intact.
- Updated README, CHANGELOG, and project status documentation.

## Not Included

- USER parsing
- FACE parsing
- FINGER parsing
- BIODATA parsing
- Command Queue
- Device command processing
- Mingdao/HAP sync
- ERP business logic
- Attendance result calculation
- Future DT007 features

## Next Development Task

DT007
