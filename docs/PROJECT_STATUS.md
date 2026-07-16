# Project Status

## Current Development Task

DT009.5

## Status

Waiting for Review

## Summary

DT009.5 adds the ADMS Server Console at `/console`. The console is a bilingual Chinese and English development-only dashboard that lets operators check server status, device online/offline state, Last Seen, Last Heartbeat, Last Data Upload, Last Raw Request, Last Request, realtime events, today's counters, and latest attendance without SSH, MySQL, tcpdump, or docker logs.

## Completed

- Added `/console` as the single console entry.
- Added Jinja2 template rendering for the console page.
- Added Chinese and English labels for the Console UI.
- Added same-path JSON data mode through `/console?format=json`.
- Added Server Status panel.
- Added top-level device online/offline banner.
- Added Device Status cards for all known devices.
- Updated Device Status to use Last Seen as the online/offline source of truth.
- Added Last Seen, Last Data Upload, Last Raw Request ID, and Last Request Type.
- Set Console offline threshold to more than 60 seconds without any device request.
- Added Realtime Event Log from existing raw request and parser result data.
- Added today's Heartbeat, ATTLOG, OPERLOG, and USER counters.
- Added Latest Attendance panel.
- Added 2-second auto refresh.
- Added Refresh button.
- Added browser-only Clear Event Log button.
- Added `scripts/DT009.5_install_ubuntu.sh`.
- Updated README, CHANGELOG, and project status documentation.

## Not Included

- Login
- Permission system
- Database schema changes
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
