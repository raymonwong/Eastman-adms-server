# ADMS System Function List

Last updated: 2026-07-19

This document lists the current core functions implemented in Eastman ADMS Server. It is written for quick review, handover, deployment discussion, and disaster-recovery planning.

## 1. System Overview

Eastman ADMS Server is the attendance-device communication server between ZKTeco ADMS attendance devices and Mingdao/HAP.

Current workflow:

```text
Mingdao Employee Master Data
        |
        v
ADMS Inbound API
        |
        v
ADMS device_user / device_user_sync / fingerprint tables
        |
        v
ZKTeco Attendance Devices
        |
        v
ATTLOG / USER / OPERLOG / FP Upload
        |
        v
ADMS Console + Mingdao Attendance Sync
```

## 2. Main Pages

| Page | URL | Purpose |
| --- | --- | --- |
| Operation Monitor | `/console` | Realtime device communication monitor, latest attendance, event log, device status, and exceptions. |
| Device Management | `/dms` | Device configuration page for attendance recording, Console visibility, device name, and location. |
| ADMS Users | `/users` | Read-only ADMS user list grouped by department, including sync state, fingerprint count, role operation, and reconciliation settings. |
| Device User Permission Management | `/devices/admin` | White-background page for Mingdao embedded custom link. Assign Normal, Admin, and Enroll Admin roles per device. |
| Inbound API | `/settings/integration` | Mingdao-to-ADMS employee API configuration, token management, API test, and integration guide. |
| Attendance Sync | `/settings/attendance-sync` | ADMS-to-Mingdao attendance synchronization configuration, manual sync, status and diagnostic log. |
| Backup Settings | `/settings/backup` | Manual backup, daily backup configuration, latest backup list, and backup download. |
| Alert Settings | `/settings/alerts` | Alert thresholds, webhook configuration, and test notification. |
| Help Center | `/settings/help` | System function help and administrator notes. |
| User Operation Guide | `/settings/user-guide` | White-background visual HR user guide for Mingdao embedded link, with English/Chinese language selection. |

## 3. ADMS Device Communication

Implemented device protocol endpoints:

| Function | Endpoint | Status |
| --- | --- | --- |
| Initial handshake | `GET/POST /iclock/cdata?options=all` | Implemented |
| Heartbeat and command polling | `GET /iclock/getrequest` | Implemented |
| Command ACK callback | `POST /iclock/devicecmd` | Implemented |
| ATTLOG upload | `POST /iclock/cdata?table=ATTLOG` | Implemented |
| OPERLOG upload | `POST /iclock/cdata?table=OPERLOG` | Implemented |
| USER upload | `POST /iclock/cdata?table=OPERLOG` with USER content | Implemented |
| Fingerprint upload | `POST /iclock/cdata?table=OPERLOG` with FP content | Implemented |

Core behavior:

- Devices are auto-discovered when they contact ADMS.
- Device heartbeat updates online status.
- Raw HTTP requests and server responses are saved in `raw_request`.
- Device events are saved in `device_event_log`.
- Invalid or unsupported HTTP payloads are visible through Uvicorn logs and Console events.
- ADMS keeps heartbeat raw rows for 3 days to avoid unlimited table growth.

## 4. Device Management

Implemented:

- Auto-register new attendance devices.
- Default new device name: `New Machine (Device SN)`.
- Edit device name.
- Edit location.
- Enable or disable attendance recording per device.
- Enable or disable Console display per device.
- Record-attendance disabled devices do not receive user/fingerprint synchronization.
- Devices are grouped visually by enabled/disabled state, with enabled devices shown first.
- Device page warns that the current deployment supports UTC+4 devices only.
- Device management page includes a saved link to the device-user permission page.

Current timezone note:

- Current deployment target timezone is Dubai time, UTC+4.
- Other timezones require a future server upgrade before adding devices.

## 5. Communication Console

Implemented in `/console`:

- Server status.
- Database status.
- API status.
- Dubai server time display.
- Device filter.
- Online device count.
- Offline device count.
- Today's attendance count.
- Today's device USER upload count.
- Mingdao user sync count.
- Today's OPLOG count.
- Exception priority panel:
  - Offline devices.
  - Heartbeat timeout.
  - Latest exception.
  - Latest normal attendance.
  - Find exception devices.
- Latest Activity table:
  - Latest 7 attendance records for the current filter.
  - New rows flash red for 5 seconds.
  - Employee name is resolved from ADMS users when available.
- Realtime Event Log:
  - Latest 10 important events for current filter.
  - Heartbeat is summarized instead of flooding the main log.
  - Event type filter.
  - Search.
  - Pause refresh.
  - Auto-scroll toggle.
  - Clear current page log.
  - Technical details can be expanded.
- Device Summary:
  - Device online/offline status.
  - Last heartbeat.
  - Last attendance.
  - Today attendance count.
  - Search and sorting controls.

## 6. Mingdao Inbound Employee API

Implemented under `/api/v1/users`.

Endpoints:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/users` | Create or update one Mingdao employee in ADMS. |
| `POST` | `/api/v1/users/batch` | Create or update up to 500 Mingdao employees. |
| `GET` | `/api/v1/users` | List ADMS users. |
| `GET` | `/api/v1/users/{employee_id}` | Get one ADMS user. |

Authentication:

- Uses `MINGDAO_API_TOKEN`.
- Supports `Authorization: Bearer <token>`.
- Supports `X-API-Key`.
- Unauthorized requests return HTTP 401.

Main fields:

- `employee_record_id`: Mingdao employee worksheet row ID. Required.
- `employee_id`: Mingdao employee number, for reference.
- `pin`: Attendance-device user number.
- `name`: Employee display name.
- `department`: Department.
- `enabled`: User active/disabled flag.
- `privilege`: Device-side privilege.

Protection:

- `employee_id` is unique.
- Duplicate `pin` owned by another employee is rejected.
- Repeated identical payload does not create duplicate users.
- Repeated identical payload does not create unnecessary sync records.
- Batch API limit is 500 users per request.
- Mingdao is the source of truth for employee master data.
- Device USER upload must not overwrite Mingdao master fields.

## 7. User Synchronization to Attendance Devices

Implemented:

- New or updated Mingdao users generate per-device sync records.
- Only devices with `record_attendance = true` receive user sync.
- Online devices receive commands through `/iclock/getrequest`.
- Offline devices keep `PENDING` records and sync after reconnect.
- Device ACK is handled by `/iclock/devicecmd`.
- Sync status values:
  - `PENDING`
  - `SYNCING`
  - `SYNCED`
  - `FAILED`
- Bounded retry is supported.
- User disable is supported: resigned or disabled employees are sent to devices as disabled users instead of being deleted immediately.
- Daily or weekly user reconciliation can recreate missing sync records.

User reconciliation:

- Configurable in the ADMS Users page.
- Supports daily or weekly schedule.
- Execution window is Dubai time 00:00-06:00.
- Shows last reconciliation time and result.
- Designed to repair cases such as manually deleted users on attendance devices.

## 8. Device User Roles

Implemented:

- Default user role is Normal.
- ADMS can assign role per user per device.
- Supported role display:
  - Normal.
  - Admin.
  - Enroll Admin.
- Admin users are sorted before Enroll Admin, then Normal users.
- Role changes are queued and delivered by `/iclock/getrequest`.
- Device applies the role after receiving the command.

Current protocol boundary:

- ADMS can set the user privilege/group value supported by the device protocol.
- Fine-grained role permission details, such as exactly which menu an Enroll Admin can access, are configured on the attendance device itself.
- ADMS currently assigns the role/group; it does not edit the internal permission menu of each role group.

## 9. Fingerprint Upload and Synchronization

Implemented:

- FP records uploaded by attendance devices are parsed from OPERLOG payloads.
- Fingerprints are saved in `device_user_fingerprint`.
- Saved fields include:
  - `device_sn`
  - `pin`
  - `finger_id`
  - `template_size`
  - `valid`
  - `template_data`
  - `template_hash`
  - `source_device_sn`
  - `raw_request_id`
- Same `pin + finger_id` with unchanged template is not duplicated.
- Same `pin + finger_id` with changed template updates the stored template.
- Console user list shows how many fingerprints are stored for each user.

Fingerprint distribution:

- Latest fingerprint template can be synchronized to other attendance devices.
- New devices receive user information and fingerprint sync tasks.
- Daily reconciliation includes fingerprint synchronization.
- Fingerprint sync failures are retried.
- Retry count is bounded and failures are visible in Console.

Current operational note:

- Fingerprint upload is triggered by device-side enrollment or update events.
- If the network is down during enrollment, upload behavior depends on the attendance device's own offline queue behavior.
- A normal punch does not necessarily re-upload the fingerprint template.

## 10. Mingdao Attendance Synchronization

Implemented in `/settings/attendance-sync`.

Configuration:

- Enable or disable attendance sync.
- Mingdao Attendance OpenAPI base URL.
- AppKey.
- Sign.
- Worksheet ID.
- Field mappings:
  - Employee Record ID.
  - Check Time.
  - Check Date.
  - Device Name.
  - Device SN.
- Failed retry interval in minutes.

Behavior:

- ADMS creates Mingdao attendance rows through Mingdao V3 OpenAPI.
- Mingdao write is create-only.
- Local duplicate prevention uses `attendance_event.id`.
- Same ADMS attendance event is not uploaded twice.
- New attendance records sync automatically.
- Manual `Sync Now` is available.
- Failed records retry according to configured interval.
- Records without `employee_record_id` are not uploaded and stay pending until the employee record ID becomes available.
- Diagnostic log shows latest sync records, sorted by priority and time.
- Diagnostic log supports pagination.
- Mingdao error messages are summarized, with detailed text available through hover/title where supported.
- Attendance time and date are sent based on the attendance device's Dubai-time punch value.

## 11. ADMS Users Console

Implemented in `/users`.

Features:

- Read-only ADMS user list.
- Grouped by department.
- GM department is shown first; other departments are sorted by department name.
- Users inside the same department are sorted by employee number.
- Disabled users are placed at the bottom to avoid taking space from active users.
- Summary cards:
  - Total users.
  - Enabled users.
  - Disabled users.
  - Department count.
  - Pending sync.
  - Fingerprint users.
- Search by employee ID, record ID, PIN, name, and department.
- Status filter.
- Sync legend:
  - P = Pending.
  - I = In progress.
  - S = Synced.
  - F = Failed.
- Per-device sync detail.
- Fingerprint count per user.
- Role action button.
- Reconciliation configuration.

## 12. Backup and Restore

Implemented under `/settings/backup`.

Backup includes:

- MySQL database dump.
- `.env` configuration.
- Docker Compose and Dockerfile.
- Python requirements.
- Restore guide.

Features:

- Manual backup from Console.
- Daily automatic backup.
- Configurable backup time.
- Configurable retention count.
- Backup host directory is fixed and read-only in the UI.
- Backup packages can be downloaded from Console.
- Latest backup records are displayed in the page.
- Restore script is provided for clean replacement server or disaster recovery.
- Cron installation script is provided for daily backup schedule.

Important restore note:

- After restoring or replacing the server, install the daily backup schedule again because Linux cron belongs to the host server, not only to the ADMS database.

## 13. Alert Center

Implemented under `/settings/alerts`.

Features:

- Enable or disable alert checks.
- Configure webhook URL.
- Configure alert check interval.
- Configure cooldown interval.
- Configure offline-device threshold.
- Configure heartbeat-timeout threshold.
- Configure failed attendance sync threshold.
- Configure failed user sync threshold.
- Configure failed fingerprint sync threshold.
- Configure backup-age threshold.
- Send test notification.
- Background alert loop runs automatically when API is running.

Alert examples:

- Device offline.
- Heartbeat timeout.
- Attendance synchronization failures.
- User synchronization failures.
- Fingerprint synchronization failures.
- Backup too old or missing.

## 14. Help Center and User Guide

Implemented:

- `/settings/help`: system help center.
- `/settings/user-guide`: visual HR operation guide.

Help center covers:

- System function overview.
- ADMS administrator notes.
- Backup and restore.
- System alerts.
- Daily reconciliation.
- User operation guide link.

User operation guide covers:

- Add a new employee.
- Enroll fingerprint.
- Set device role.
- Add a new device.
- Backup and restore.
- System alerts.
- Daily reconciliation.

User guide behavior:

- White-background visual page.
- English and Chinese language selector.
- Default language follows browser/user language when possible.
- Designed to be opened from Mingdao custom links.

## 15. Deployment and Verification

Current recommended deployment script:

```bash
bash scripts/DT017.1_install_ubuntu.sh
```

The installation chain verifies:

- Database readiness.
- ADMS protocol endpoints.
- Device registration.
- ATTLOG, OPERLOG, USER and fingerprint handling.
- Console pages.
- Device management.
- User synchronization.
- Mingdao inbound API.
- Mingdao attendance sync.
- Backup settings.
- Alert settings.
- Help center.
- User operation guide.

## 16. Current Known Boundaries

Implemented system does not currently provide:

- HTTPS without domain and certificate configuration.
- Login or permission system for ADMS Console.
- Face template synchronization.
- User photo synchronization.
- Password synchronization.
- Attendance result calculation such as late, early leave, missing punch, or in/out direction.
- Cross-timezone automatic device scheduling beyond the current UTC+4 deployment target.
- Editing attendance-device internal role-menu permission details from ADMS.

## 17. One-Page Summary

Current ADMS already supports:

- Automatic device registration.
- Device heartbeat monitoring.
- Attendance upload collection.
- Operation log collection.
- User upload collection.
- Fingerprint upload collection.
- Mingdao employee import API.
- User synchronization to attendance devices.
- User role assignment to devices.
- Fingerprint distribution to devices.
- Mingdao attendance upload with duplicate prevention.
- Operation Monitor Console.
- Device Management page.
- ADMS Users page.
- Device User Permission Management page.
- Inbound API configuration.
- Attendance Sync configuration.
- Backup and restore.
- Alert center.
- Help center.
- Visual HR user operation guide.

