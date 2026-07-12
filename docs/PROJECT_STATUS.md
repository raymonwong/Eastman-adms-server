# Project Status

## Current Development Task

DT008

## Status

Waiting for Review

## Summary

DT008 extends the OPERLOG parser for real device USER uploads. Real devices upload new user data inside `POST /iclock/cdata?table=OPERLOG`, so the server now parses `USER` body records and stores them in `device_user`.

## Completed

- Added `device_user` table.
- Added unique user key by `device_sn` and `pin`.
- Added USER parser for `PIN`, `Name`, `Pri`, `Passwd`, `Card`, `Grp`, `TZ`, `Verify`, `ViceCard`, `StartDatetime`, and `EndDatetime`.
- Added upsert behavior for repeated USER uploads from the same device and PIN.
- Extended OPERLOG parser dispatch so `OPLOG` continues to save `operation_event` and `USER` saves `device_user`.
- Kept `raw_request` persistence unchanged.
- Kept ATTLOG and OPLOG behavior compatible.
- Added `scripts/DT008_install_ubuntu.sh`.
- Updated README, CHANGELOG, and project status documentation.

## Not Included

- Dynamic ATTLOGStamp response
- Dynamic OPERLOGStamp response
- FACE parsing
- FINGER parsing
- Command Queue
- Device command processing
- User downlink
- Personnel synchronization
- Mingdao/HAP sync
- ERP business logic
- Attendance result calculation
- Future DT009 features

## Next Development Task

DT009
