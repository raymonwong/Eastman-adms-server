# Project Status

## Current Development Task

DT004

## Status

Waiting for Review

## Summary

DT004 implements the ADMS initialization handshake from the official ZKTeco PUSH protocol V4.3 chapter 6. The server responds to `GET /iclock/cdata?options=all` with `GET OPTION FROM:` configuration data, stores the original request and response snapshot, and updates device handshake metadata.

## Completed

- Added official `GET OPTION FROM:` response for initialization handshake.
- Added default `9999` stamps when no server-side stamp record exists.
- Added `TimeZone=4`, `Realtime=1`, `Delay=10`, `ErrorDelay=30`, `TransInterval=1`, and `TransTimes=00:00`.
- Added official TransFlag format two with `AttLog`, `OpLog`, `EnrollUser`, `ChgUser`, `EnrollFP`, `ChgFP`, `FACE`, and `UserPic`.
- Added `PushProtVer=2.4.2`, `PushOptionsFlag=1`, and default push options.
- Added `device` handshake metadata fields.
- Added `scripts/DT004_install_ubuntu.sh`.
- Kept DT003 request capture, ATTLOG upload compatibility, OPERLOG upload compatibility, `getrequest`, and `devicecmd` behavior untouched.
- Updated README, CHANGELOG, and project status documentation.

## Not Included

- ADMS business logic
- Attendance parsing
- User synchronization
- Device commands
- Command Queue
- Mingdao/HAP sync
- Future DT005 features

## Next Development Task

DT005
