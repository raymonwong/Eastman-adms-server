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
  "employee_id": "10001",
  "name": "Raymon",
  "department": "IT",
  "card_no": "",
  "privilege": 0,
  "enabled": true
}
```

Response:

```json
{
  "success": true,
  "employee_id": "10001",
  "message": "User synchronized successfully.",
  "changed": true,
  "sync_records": 1
}
```

If the same payload is sent again, ADMS returns success with `changed=false` and `sync_records=0`.

### POST /api/v1/users/batch

Purpose:

Create or update multiple Mingdao employees in one request.

Limit:

Maximum 500 users per request.

Request body:

```json
[
  {
    "employee_id": "10001",
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
GET /api/v1/users/10001
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
  "employee_id": "10001",
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
  "employee_id": "10001",
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
{"detail":[{"msg":"Value error, unsupported privilege: 99"}]}
```

## 5. Synchronization Flow

Current DT010.1 synchronization flow:

```text
Mingdao
  -> REST API
  -> device_user
  -> device_user_sync
  -> Attendance Device
```

When a Mingdao user is created or changed, ADMS creates or updates one `device_user_sync` record for every registered device and sets it to `PENDING`.

Online device:

```text
Mingdao update
  -> PENDING sync record
  -> Device GETREQUEST sees pending sync
  -> Command delivery will be implemented in a later task
```

Offline device:

```text
Mingdao update
  -> PENDING sync record
  -> Device reconnects later
  -> Automatic synchronization can be performed in a later task
```

DT010.1 and DT010.11 do not implement actual user download commands.

## 6. Troubleshooting

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
