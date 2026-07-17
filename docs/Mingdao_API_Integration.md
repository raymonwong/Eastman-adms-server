# Mingdao API Integration

## 1. System Overview

Eastman ADMS Server uses the following integration flow:

```text
Mingdao
  -> REST API
  -> ADMS Server
  -> Attendance Device
```

Mingdao is the master employee database. ADMS is responsible for attendance device communication, ADMS protocol handling, raw request storage, ATTLOG parsing, OPERLOG parsing, USER upload recording, and device synchronization state.

Employee information must always originate from Mingdao. Administrators must not edit ADMS database records directly.

## 2. Authentication

All Mingdao user APIs are protected by a simple API token.

The token is configured in `.env`:

```env
MINGDAO_API_TOKEN=replace-with-a-secure-token
```

Requests may use either header:

```http
Authorization: Bearer <API_TOKEN>
```

or:

```http
X-API-Key: <API_TOKEN>
```

If the token is missing, still set to the default placeholder, or invalid, ADMS returns HTTP `401`.

## 3. Available APIs

Base URL:

```text
http://<server-ip>:4370/api/v1
```

### POST /api/v1/users

Purpose:

Create or update one Mingdao employee in ADMS.

Headers:

```http
Authorization: Bearer <API_TOKEN>
Content-Type: application/json
```

Request body:

```json
{
  "employee_record_id": "659823456789",
  "employee_id": "ESM0001",
  "pin": "1",
  "name": "Raymon",
  "department": "IT",
  "card_no": "",
  "privilege": 0,
  "enabled": true
}
```

`employee_record_id` must be the Mingdao employee worksheet record ID. DT014 Attendance Synchronization will use this value to populate the Mingdao employee relation field directly, so Mingdao workflows will not be required to associate attendance records with employees.

`employee_id` is retained as the Mingdao/ERP employee number for reference and future business matching. `pin` is the attendance device user number and is the field that future device update commands must use. For example, `ESM0001` should be sent as `employee_id=ESM0001` and `pin=1`. If `pin` is omitted, ADMS keeps backward compatibility and uses `employee_id` as the PIN. In production integrations, send all three identifiers: `employee_record_id`, `employee_id`, and `pin`.

Response:

```json
{
  "success": true,
  "employee_id": "ESM0001",
  "employee_record_id": "659823456789",
  "pin": "1",
  "message": "User synchronized successfully.",
  "changed": true,
  "sync_records": 1
}
```

If the same payload is sent again, ADMS returns success with `changed=false` and `sync_records=0`.

If another employee already owns the same `pin`, ADMS rejects the request with HTTP `409 Conflict`.

### POST /api/v1/users/batch

Purpose:

Create or update multiple Mingdao employees in one request.

Limit:

Maximum 500 users per request.

Request body:

```json
[
  {
    "employee_record_id": "659823456789",
    "employee_id": "ESM0001",
    "pin": "1",
    "name": "Raymon",
    "department": "IT",
    "card_no": "",
    "privilege": 0,
    "enabled": true
  }
]
```

Response:

```json
{
  "success": true,
  "total": 1,
  "succeeded": 1,
  "failed": 0,
  "results": []
}
```

### GET /api/v1/users

Purpose:

List current Mingdao-sourced users.

Headers:

```http
Authorization: Bearer <API_TOKEN>
```

### GET /api/v1/users/{employee_id}

Purpose:

Get one Mingdao-sourced user by employee ID.

Example:

```http
GET /api/v1/users/ESM0001
```

## 4. Mingdao Configuration Guide

Configure a Mingdao HTTP request node with:

Request URL:

```text
http://<server-ip>:4370/api/v1/users
```

Request Method:

```text
POST
```

Headers:

```http
Authorization: Bearer <API_TOKEN>
Content-Type: application/json
```

Request JSON example:

```json
{
  "employee_record_id": "659823456789",
  "employee_id": "ESM0001",
  "pin": "1",
  "name": "Raymon",
  "department": "IT",
  "card_no": "",
  "privilege": 0,
  "enabled": true
}
```

Successful response example:

```json
{
  "success": true,
  "employee_id": "ESM0001",
  "employee_record_id": "659823456789",
  "pin": "1",
  "message": "User synchronized successfully.",
  "changed": true,
  "sync_records": 1
}
```

Error response examples:

```json
{"detail":"Invalid Mingdao API token."}
```

```json
{"detail":"Batch size exceeds maximum limit of 500 users."}
```

```json
{"detail":[{"msg":"Field required","loc":["body","employee_record_id"]}]}
```

```json
{"detail":[{"msg":"Value error, unsupported privilege: 99"}]}
```

## 5. User Synchronization Flow

Current DT011 synchronization flow:

```text
Mingdao
  -> REST API
  -> device_user
  -> device_user_sync
  -> /iclock/getrequest
  -> DATA UPDATE USERINFO
  -> Attendance Device
  -> /iclock/devicecmd ACK
  -> Attendance Device
```

When a Mingdao user is created or changed, ADMS creates or updates one `device_user_sync` record for every participating registered device and sets it to `PENDING`.

Only devices with `record_attendance = true` participate in Mingdao user
synchronization. Devices with `record_attendance = false` continue to connect to
ADMS, but they do not receive user sync records or USERINFO commands. If an
administrator later changes the device back to `record_attendance = true`, ADMS
rebuilds missing `PENDING` sync records for all Mingdao users on that device.

Online device:

```text
Mingdao update
  -> PENDING sync record
  -> Device GETREQUEST
  -> Server returns C:<sync_id>:DATA UPDATE USERINFO ...
  -> sync_status = SYNCING
  -> Device POST /iclock/devicecmd
  -> sync_status = SYNCED or FAILED
```

Offline device:

```text
Mingdao update
  -> PENDING sync record
  -> Device reconnects later
  -> Next GETREQUEST receives the pending command
```

### Command Format

DT011 sends one user command at a time during `/iclock/getrequest`:

```text
C:<sync_id>:DATA UPDATE USERINFO PIN=<pin>	Name=<name>	Pri=<privilege>	Passwd=	Card=<card_no>	Grp=1	TZ=0000000100000000	Verify=1	ViceCard=	StartDatetime=0	EndDatetime=0
```

`sync_id` is the `device_user_sync.id` value and is used to match the later device ACK.

If the attendance device already has the same `PIN`, `DATA UPDATE USERINFO`
updates the existing device user. ADMS still rejects duplicate `pin` values
across different Mingdao employees to avoid overwriting the wrong person on the
device.

### ACK Format

After executing a command, the device posts to:

```text
POST /iclock/devicecmd?SN=<device_sn>
```

The server accepts common ADMS ACK formats, including:

```text
ID=<sync_id>&Return=0
```

`Return=0`, `OK`, `SUCCESS`, or an empty result is treated as success. Other result values mark the sync as `FAILED`.

### Sync Status

| Status | Meaning |
| --- | --- |
| `PENDING` | User change is waiting for this device. |
| `SYNCING` | Command has been returned to the device and ADMS is waiting for `/iclock/devicecmd`. |
| `SYNCED` | Device acknowledged success. |
| `FAILED` | Device returned an error or ADMS could not build the command. |

### Retry

`USER_SYNC_MAX_RETRY` controls retry limit. Default:

```env
USER_SYNC_MAX_RETRY=3
```

`USER_SYNC_ACK_TIMEOUT_SECONDS` controls how long a `SYNCING` command can wait before it is eligible for resend. Default:

```env
USER_SYNC_ACK_TIMEOUT_SECONDS=120
```

DT011 does not implement fingerprint, face, photo, password, or delete commands.

## 6. Attendance Synchronization

DT014 uploads saved ADMS `attendance_event` records to Mingdao Attendance.
It only creates Mingdao worksheet rows. It does not update existing Mingdao rows.

Location:

```text
Communication Console
  -> System Settings
  -> Integration
  -> Attendance Synchronization
```

### Configuration Items

| Item | Purpose |
| --- | --- |
| Enable Attendance Synchronization | Enables or disables Mingdao attendance synchronization. |
| Mingdao Attendance OpenAPI URL | Complete Mingdao OpenAPI base URL or worksheet schema URL. Do not hardcode it in code. |
| AppKey | Mingdao OpenAPI AppKey copied from Mingdao OpenAPI authorization page. |
| Sign | Mingdao OpenAPI Sign copied from Mingdao OpenAPI authorization page. |
| Worksheet ID | Mingdao Attendance worksheet ID copied from Mingdao OpenAPI documentation. |
| Employee Record ID Target Field ID | Target Mingdao field ID for the employee relation/record ID. |
| Check Time Target Field ID | Target Mingdao field ID for attendance check time. |
| Device Name Target Field ID | Target Mingdao field ID for ADMS device name. |
| Device SN Target Field ID | Target Mingdao field ID for ADMS device serial number. |
| Retry Failed After Minutes | Failed records become eligible for another create-row attempt after this interval. |

Mingdao OpenAPI authentication uses the official headers:

```http
HAP-Appkey: <AppKey>
HAP-Sign: <Sign>
```

The existing ADMS `MINGDAO_API_TOKEN` is reused as the ADMS-side API protection token. DT013.1 does not create a second ADMS token.

### Connection Test

The Test Connection button performs a read-only worksheet metadata check.

It builds the worksheet schema URL as:

```text
<Mingdao Attendance OpenAPI URL>/v3/app/worksheets/<Worksheet ID>
```

If the configured OpenAPI URL already contains `/v3/app/worksheets/` or `{worksheet_id}`, ADMS uses it directly or substitutes `{worksheet_id}`.

The connection test verifies:

- OpenAPI URL is valid.
- AppKey and Sign are present.
- Worksheet ID is present.
- Mingdao OpenAPI is reachable.
- Worksheet metadata returns successfully.
- Configured target field IDs exist in the returned worksheet metadata.

The connection test does not write attendance records.

### Mingdao Create Row Request

DT014 writes to the official Mingdao V3 create-record API:

```text
POST /v3/app/worksheets/{worksheet_id}/rows
```

Headers:

```http
HAP-Appkey: <AppKey>
HAP-Sign: <Sign>
Content-Type: application/json
```

Request body:

```json
{
  "triggerWorkflow": true,
  "fields": [
    {
      "id": "<Employee Record ID Target Field ID>",
      "value": "<device_user.employee_record_id>"
    },
    {
      "id": "<Check Time Target Field ID>",
      "value": "2026-07-17 20:50:02"
    },
    {
      "id": "<Device Name Target Field ID>",
      "value": "CT ShowRoom"
    },
    {
      "id": "<Device SN Target Field ID>",
      "value": "UCE6262000016"
    }
  ]
}
```

### Duplicate Prevention

DT014 must not upload duplicate attendance records to Mingdao.

The required duplicate prevention rule is:

```text
One ADMS attendance_event.id -> at most one Mingdao attendance record
```

DT014 uses `attendance_event.id` as the local idempotency key before writing to Mingdao.
The local table `attendance_mingdao_sync` has a unique constraint on `attendance_event_id`.
Records with `SYNCED` status are never uploaded again.

After a successful upload, ADMS stores the Mingdao row ID when it is returned by Mingdao. Retry logic can distinguish:

- Not uploaded yet.
- Uploaded successfully.
- Failed and eligible for retry.
- Already uploaded and must be skipped.

This design is intentional because device-level duplicate protection and ATTLOG parser uniqueness are not sufficient to protect downstream Mingdao writes during network retries.

### Retry

New `attendance_event` records are registered as `PENDING` and uploaded by the background synchronization loop.
The loop runs every 10 seconds by default:

```env
MINGDAO_ATTENDANCE_AUTO_SYNC_INTERVAL_SECONDS=10
```

Failed records stay `FAILED`. They become eligible for another Mingdao create-row attempt only after:

```env
MINGDAO_ATTENDANCE_RETRY_FAILED_AFTER_MINUTES=60
```

This retry still uses the same local idempotency key, so a record already marked `SYNCED` is not uploaded again.

## 7. Troubleshooting

### 401 Unauthorized

The request is missing a token, using the wrong token, or the server still has the default placeholder token.

### Invalid API Token

Check `.env`:

```env
MINGDAO_API_TOKEN=replace-with-a-secure-token
```

Restart the API service after changing `.env`.

### 404 API Not Found

Confirm the path starts with:

```text
/api/v1
```

### API Timeout

Confirm the ADMS server is reachable on port `4370`.

### Device Offline

The user sync record remains `PENDING` until the device reconnects.

### Pending Synchronization

Check Communication Console -> System Settings -> Integration and Operation Monitor.

### No Online Device

Open `/console` and check device heartbeat status.

### No API Request Received

Check Mingdao HTTP node URL, headers, token, server public IP, and network access.
