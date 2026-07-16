import hashlib
import json
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models import AttendanceEvent, Device, DeviceEventLog, DeviceSyncState, DeviceUser, OperationEvent, RawRequest

router = APIRouter()

PUSH_PROTOCOL_VERSION = "2.4.2"
DUBAI_TIMEZONE = "4"
DEFAULT_STAMP = "9999"
DEFAULT_DELAY = "10"
DEFAULT_ERROR_DELAY = "30"
DEFAULT_REALTIME = "1"
DEFAULT_TRANS_INTERVAL = "1"
DEFAULT_TRANS_TIMES = "00:00"
DEFAULT_TRANS_FLAG = "TransData\tAttLog\tOpLog\tEnrollUser\tChgUser\tEnrollFP\tChgFP\tFACE\tUserPic"
DEFAULT_PUSH_OPTIONS = "FingerFunOn,FaceFunOn,UserPicURLFunOn"
OPERATION_NAME_MAP = {
    "82": "Modify Cloud Server Address",
}
SYNC_DATA_TYPES = ("ATTLOG", "OPERLOG", "USER", "FINGER", "FACE", "PHOTO")


def _debug_log(event_type: str, fields: dict[str, object | None]) -> None:
    # Keep ADMS development logs readable in `docker logs -f eastman-adms-api`.
    print("==================================================", flush=True)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]", flush=True)
    print(event_type, flush=True)
    print("", flush=True)
    for label, value in fields.items():
        print(f"{label}:", flush=True)
        print("" if value is None else str(value), flush=True)
        print("", flush=True)
    print("==================================================", flush=True)
    print("", flush=True)


def _json_dump(value: object) -> str:
    # Preserve non-ASCII device values while keeping a structured snapshot.
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _decode_body(raw_body: bytes) -> str:
    # Latin-1 maps bytes 1:1, so future parsers can reconstruct the exact payload.
    return raw_body.decode("latin-1")


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else None


def _request_hash(
    method: str,
    url: str,
    headers: str,
    body: bytes,
    client_ip: str | None,
) -> str:
    digest = hashlib.sha256()
    digest.update(method.encode("utf-8"))
    digest.update(b"\n")
    digest.update(url.encode("utf-8"))
    digest.update(b"\n")
    digest.update(headers.encode("utf-8"))
    digest.update(b"\n")
    digest.update(client_ip.encode("utf-8") if client_ip else b"")
    digest.update(b"\n")
    digest.update(body)
    return digest.hexdigest()


def _upsert_device(
    device_sn: str | None,
    ip_address: str | None,
    received_at: datetime,
    *,
    handshake: bool = False,
    push_version: str | None = None,
    device_type: str | None = None,
    language: str | None = None,
    push_options: str | None = None,
) -> int | None:
    if not device_sn:
        return None

    with SessionLocal() as session:
        device = session.query(Device).filter(Device.device_sn == device_sn).one_or_none()
        if device is None:
            device = Device(
                device_sn=device_sn,
                device_name=f"New Machine ({device_sn})",
                ip_address=ip_address,
                first_online=received_at,
                last_online=received_at,
                status="online",
                record_attendance=True,
                show_in_console=True,
            )
            session.add(device)
        else:
            if not device.device_name:
                device.device_name = f"New Machine ({device_sn})"
            device.ip_address = ip_address
            device.last_online = received_at
        if handshake:
            device.last_handshake_time = received_at
            device.push_version = push_version
            device.device_type = device_type
            device.language = language
            device.push_options = push_options
        session.commit()
        return device.id


def _device_records_attendance(device_sn: str | None) -> bool:
    if not device_sn:
        return True

    with SessionLocal() as session:
        device = session.query(Device).filter(Device.device_sn == device_sn).one_or_none()
        if device is None:
            return True
        return bool(device.record_attendance)


def _is_initialization_handshake(request: Request) -> bool:
    return request.method == "GET" and request.query_params.get("options", "").lower() == "all"


def _is_attlog_upload(request: Request) -> bool:
    return request.method == "POST" and request.query_params.get("table", "").upper() == "ATTLOG"


def _is_operlog_upload(request: Request) -> bool:
    return request.method == "POST" and request.query_params.get("table", "").upper() == "OPERLOG"


def _request_stamp(request: Request) -> str | None:
    return request.query_params.get("Stamp") or request.query_params.get("stamp") or request.query_params.get("OpStamp")


def _build_initialization_response(device_sn: str | None) -> str:
    # DT007 reads sync state for future Stamp management but keeps fixed Stamp output.
    _get_device_sync_states(device_sn)
    sn = device_sn or ""
    lines = [
        f"GET OPTION FROM: {sn}",
        f"ATTLOGStamp={DEFAULT_STAMP}",
        f"OPERLOGStamp={DEFAULT_STAMP}",
        f"ATTPHOTOStamp={DEFAULT_STAMP}",
        f"ERRORLOGStamp={DEFAULT_STAMP}",
        f"Delay={DEFAULT_DELAY}",
        f"ErrorDelay={DEFAULT_ERROR_DELAY}",
        f"Realtime={DEFAULT_REALTIME}",
        f"TransInterval={DEFAULT_TRANS_INTERVAL}",
        f"TransTimes={DEFAULT_TRANS_TIMES}",
        f"TransFlag={DEFAULT_TRANS_FLAG}",
        f"TimeZone={DUBAI_TIMEZONE}",
        "Encrypt=0",
        f"PushProtVer={PUSH_PROTOCOL_VERSION}",
        "PushOptionsFlag=1",
        f"PushOptions={DEFAULT_PUSH_OPTIONS}",
        f"ServerVer={PUSH_PROTOCOL_VERSION}",
    ]
    return "\n".join(lines)


def _save_raw_request(request: Request, body: bytes, response_body: str, response_status_code: int) -> dict[str, object]:
    received_at = datetime.now(UTC)
    method = request.method
    url = str(request.url)
    query_string = request.url.query
    query_params = list(request.query_params.multi_items())
    headers = [(key.decode("latin-1"), value.decode("latin-1")) for key, value in request.scope.get("headers", [])]
    headers_json = _json_dump(headers)
    client_ip = _client_ip(request)
    device_sn = request.query_params.get("SN") or request.query_params.get("sn")
    request_hash = _request_hash(method, url, headers_json, body, client_ip)

    raw_request = RawRequest(
        device_sn=device_sn,
        request_method=method,
        request_url=url,
        request_path=request.url.path,
        query_string=query_string,
        query_params=_json_dump(query_params),
        headers=headers_json,
        body=_decode_body(body),
        client_ip=client_ip,
        user_agent=request.headers.get("user-agent"),
        content_type=request.headers.get("content-type"),
        response_body=response_body,
        response_status_code=response_status_code,
        request_size=len(body),
        response_size=len(response_body.encode("utf-8")),
        request_hash=request_hash,
        received_at=received_at,
    )

    with SessionLocal() as session:
        session.add(raw_request)
        session.flush()
        raw_request_id = raw_request.id
        session.commit()

    return {
        "raw_request_id": raw_request_id,
        "device_sn": device_sn,
        "client_ip": client_ip,
        "received_at": received_at,
        "method": method,
        "url": url,
        "response_body": response_body,
        "response_status_code": response_status_code,
        "user_agent": request.headers.get("user-agent"),
        "request_hash": request_hash,
    }


def _update_raw_request_response(raw_request_id: int, response_body: str, response_status_code: int) -> None:
    with SessionLocal() as session:
        raw_request = session.get(RawRequest, raw_request_id)
        if raw_request is None:
            return
        raw_request.response_body = response_body
        raw_request.response_status_code = response_status_code
        raw_request.response_size = len(response_body.encode("utf-8"))
        session.commit()


def _mark_raw_request_parsed(raw_request_id: int) -> None:
    with SessionLocal() as session:
        raw_request = session.get(RawRequest, raw_request_id)
        if raw_request is None:
            return
        raw_request.parsed = True
        session.commit()


def _get_device_sync_states(device_sn: str | None) -> dict[str, str | None]:
    if not device_sn:
        return {}
    if SessionLocal.kw.get("bind") is None:
        return {}

    with SessionLocal() as session:
        states = session.query(DeviceSyncState).filter(DeviceSyncState.device_sn == device_sn).all()
        return {state.data_type: state.device_stamp for state in states}


def _update_device_sync_state(context: dict[str, object], data_type: str, device_stamp: str | None) -> None:
    device_sn = context["device_sn"]
    if not device_sn:
        return

    normalized_type = data_type.upper()
    if normalized_type not in SYNC_DATA_TYPES:
        return

    with SessionLocal() as session:
        state = (
            session.query(DeviceSyncState)
            .filter(DeviceSyncState.device_sn == device_sn, DeviceSyncState.data_type == normalized_type)
            .one_or_none()
        )
        if state is None:
            state = DeviceSyncState(device_sn=device_sn, data_type=normalized_type)
            session.add(state)

        state.device_stamp = device_stamp
        state.last_success_time = context["received_at"]
        state.last_raw_request_id = context["raw_request_id"]
        session.commit()

    _debug_log(
        "SYNC STATE UPDATED",
        {
            "Device": device_sn,
            "Data Type": normalized_type,
            "Device Stamp": device_stamp or "",
            "Raw Request ID": context["raw_request_id"],
        },
    )


def _save_device_event(context: dict[str, object], device_id: int | None, remark: str | None) -> None:
    event = DeviceEventLog(
        event_type="Connect",
        device_sn=context["device_sn"],
        device_id=device_id,
        client_ip=context["client_ip"],
        connect_time=context["received_at"],
        method=context["method"],
        url=context["url"],
        status_code=context["response_status_code"],
        response=context["response_body"],
        user_agent=context["user_agent"],
        request_hash=context["request_hash"],
        remark=remark,
    )

    with SessionLocal() as session:
        session.add(event)
        session.commit()


def _log_device_connection(
    device_sn: str | None,
    client_ip: str | None,
    received_at: datetime,
    method: str,
    url: str,
    response_body: str,
    response_status_code: int,
) -> None:
    _debug_log(
        "DEVICE CONNECTED",
        {
            "Device": device_sn or "",
            "Client IP": client_ip or "",
            "Method": method,
            "URL": url,
            "Response": response_body,
            "Status": response_status_code,
        },
    )


def _log_initialization_completed(
    device_sn: str | None,
    client_ip: str | None,
    push_version: str | None,
    response_body: str,
) -> None:
    _debug_log(
        "HANDSHAKE",
        {
            "Device": device_sn or "",
            "Client IP": client_ip or "",
            "Push Version": push_version or "",
            "Response": response_body,
        },
    )


def _parse_attlog_line(line: str, device_sn: str | None, receive_time: datetime, raw_request_id: int) -> AttendanceEvent:
    fields = line.split("\t")
    if len(fields) < 6:
        raise ValueError("ATTLOG record must contain at least 6 tab-separated fields")

    pin, attendance_time_text, status, verify, work_code, reserved1 = fields[:6]
    reserved2 = fields[6] if len(fields) > 6 else None
    mask_flag = fields[7] if len(fields) > 7 else None
    temperature = fields[8] if len(fields) > 8 else None
    conv_temperature = fields[9] if len(fields) > 9 else None
    if not device_sn:
        raise ValueError("ATTLOG record is missing device SN")
    if not pin:
        raise ValueError("ATTLOG record is missing PIN")

    attendance_time = datetime.strptime(attendance_time_text, "%Y-%m-%d %H:%M:%S")
    return AttendanceEvent(
        device_sn=device_sn,
        pin=pin,
        attendance_time=attendance_time,
        status=status,
        verify=verify,
        work_code=work_code,
        reserved1=reserved1,
        reserved2=reserved2,
        mask_flag=mask_flag,
        temperature=temperature,
        conv_temperature=conv_temperature,
        receive_time=receive_time,
        raw_request_id=raw_request_id,
    )


def _save_attendance_event(event: AttendanceEvent) -> bool:
    with SessionLocal() as session:
        session.add(event)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            return False
    return True


def _parse_and_save_attlog(context: dict[str, object], body: bytes) -> int:
    body_text = _decode_body(body)
    saved_count = 0

    for line_number, line in enumerate(body_text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = _parse_attlog_line(
                line,
                context["device_sn"],
                context["received_at"],
                context["raw_request_id"],
            )
        except Exception as exc:
            _debug_log(
                "ERROR",
                {
                    "Device": context["device_sn"] or "",
                    "Module": "ATTLOG",
                    "Reason": f"Line {line_number}: {exc}",
                },
            )
            continue

        _debug_log(
            "ATTLOG RECEIVED",
            {
                "Device": event.device_sn,
                "PIN": event.pin,
                "Attendance Time": event.attendance_time,
            },
        )

        if not _save_attendance_event(event):
            continue

        saved_count += 1
        _debug_log(
            "ATTLOG SAVED",
            {
                "Attendance ID": event.id,
                "Raw Request ID": event.raw_request_id,
            },
        )

    return saved_count


def _operation_name(operation_code: str) -> str:
    return OPERATION_NAME_MAP.get(operation_code, f"Operation {operation_code}")


def _parse_operlog_line(line: str, device_sn: str | None, receive_time: datetime, raw_request_id: int) -> OperationEvent:
    uses_tabs = "\t" in line
    fields = line.split("\t") if uses_tabs else line.split()
    if not fields:
        raise ValueError("OPERLOG record is empty")
    if fields[0].upper() != "OPLOG":
        raise ValueError("OPERLOG record must start with OPLOG")

    payload = fields[1:]
    if len(payload) < 3:
        raise ValueError("OPERLOG record is missing required fields")

    if not device_sn:
        raise ValueError("OPERLOG record is missing device SN")

    operation_code = payload[0]
    if not operation_code:
        raise ValueError("OPERLOG record is missing operation code")

    operator = payload[1] if len(payload) > 1 else None
    if uses_tabs:
        operation_time_text = payload[2]
        optional_fields = payload[3:]
    else:
        if len(payload) < 4:
            raise ValueError("OPERLOG record is missing operation time")
        # Real devices may separate fields by spaces, which splits the timestamp into date and time tokens.
        operation_time_text = f"{payload[2]} {payload[3]}"
        optional_fields = payload[4:]

    operation_time = datetime.strptime(operation_time_text, "%Y-%m-%d %H:%M:%S")
    operation_object = optional_fields[0] if len(optional_fields) > 0 else None
    value1 = optional_fields[1] if len(optional_fields) > 1 else None
    value2 = optional_fields[2] if len(optional_fields) > 2 else None
    value3 = optional_fields[3] if len(optional_fields) > 3 else None

    return OperationEvent(
        device_sn=device_sn,
        operation_code=operation_code,
        operation_name=_operation_name(operation_code),
        operator=operator,
        operation_time=operation_time,
        operation_object=operation_object,
        value1=value1,
        value2=value2,
        value3=value3,
        receive_time=receive_time,
        raw_request_id=raw_request_id,
    )


def _save_operation_event(event: OperationEvent) -> int:
    with SessionLocal() as session:
        session.add(event)
        session.commit()
        return event.id


def _parse_key_value_fields(fields: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for field in fields:
        if "=" not in field:
            continue
        key, value = field.split("=", 1)
        if key:
            values[key.lower()] = value
    return values


def _parse_user_line(line: str, device_sn: str | None, receive_time: datetime, raw_request_id: int) -> DeviceUser:
    fields = line.split()
    if not fields or fields[0].upper() != "USER":
        raise ValueError("USER record must start with USER")
    if not device_sn:
        raise ValueError("USER record is missing device SN")

    values = _parse_key_value_fields(fields[1:])
    pin = values.get("pin")
    if not pin:
        raise ValueError("USER record is missing PIN")

    return DeviceUser(
        device_sn=device_sn,
        pin=pin,
        name=values.get("name"),
        privilege=values.get("pri"),
        password=values.get("passwd"),
        card=values.get("card"),
        group_no=values.get("grp"),
        timezone=values.get("tz"),
        verify_mode=values.get("verify"),
        vice_card=values.get("vicecard"),
        start_datetime=values.get("startdatetime"),
        end_datetime=values.get("enddatetime"),
        raw_request_id=raw_request_id,
        receive_time=receive_time,
    )


def _save_device_user(user: DeviceUser) -> int:
    with SessionLocal() as session:
        existing_user = (
            session.query(DeviceUser)
            .filter(DeviceUser.device_sn == user.device_sn, DeviceUser.pin == user.pin)
            .one_or_none()
        )
        if existing_user is None:
            session.add(user)
        else:
            existing_user.name = user.name
            existing_user.privilege = user.privilege
            existing_user.password = user.password
            existing_user.card = user.card
            existing_user.group_no = user.group_no
            existing_user.timezone = user.timezone
            existing_user.verify_mode = user.verify_mode
            existing_user.vice_card = user.vice_card
            existing_user.start_datetime = user.start_datetime
            existing_user.end_datetime = user.end_datetime
            existing_user.raw_request_id = user.raw_request_id
            existing_user.receive_time = user.receive_time
        session.commit()
        return existing_user.id if existing_user is not None else user.id


def _parse_and_save_operlog(context: dict[str, object], body: bytes) -> int:
    body_text = _decode_body(body)
    saved_count = 0

    for line_number, line in enumerate(body_text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record_type = line.split(None, 1)[0].upper()
            if record_type == "OPLOG":
                event = _parse_operlog_line(
                    line,
                    context["device_sn"],
                    context["received_at"],
                    context["raw_request_id"],
                )
                _debug_log(
                    "OPERLOG RECEIVED",
                    {
                        "Device": event.device_sn,
                        "Operation": event.operation_code,
                        "Operation Time": event.operation_time,
                    },
                )
                operation_id = _save_operation_event(event)
                saved_count += 1
                _debug_log(
                    "OPERLOG SAVED",
                    {
                        "Operation ID": operation_id,
                    },
                )
            elif record_type == "USER":
                user = _parse_user_line(
                    line,
                    context["device_sn"],
                    context["received_at"],
                    context["raw_request_id"],
                )
                _debug_log(
                    "USER RECEIVED",
                    {
                        "Device": user.device_sn,
                        "PIN": user.pin,
                        "User Name": user.name or "",
                    },
                )
                user_id = _save_device_user(user)
                saved_count += 1
                _debug_log(
                    "USER SAVED",
                    {
                        "User ID": user_id,
                    },
                )
            else:
                raise ValueError(f"unsupported OPERLOG record type: {record_type}")
        except Exception as exc:
            module = record_type if "record_type" in locals() else "OPERLOG"
            _debug_log(
                "ERROR",
                {
                    "Device": context["device_sn"] or "",
                    "Module": "USER" if module == "USER" else "OPERLOG",
                    "Reason": f"Line {line_number}: {exc}",
                },
            )
            continue

    return saved_count


@router.api_route("/iclock/cdata", methods=["GET", "POST"])
async def iclock_cdata(request: Request) -> PlainTextResponse:
    device_sn = request.query_params.get("SN") or request.query_params.get("sn")
    is_handshake = _is_initialization_handshake(request)
    is_attlog = _is_attlog_upload(request)
    is_operlog = _is_operlog_upload(request)
    response_body = _build_initialization_response(device_sn) if is_handshake else "OK"
    response_status_code = 200
    body = await request.body()
    context = _save_raw_request(request, body, response_body, response_status_code)

    device_id = None
    remark = None
    try:
        device_id = _upsert_device(
            context["device_sn"],
            context["client_ip"],
            context["received_at"],
            handshake=is_handshake,
            push_version=request.query_params.get("pushver"),
            device_type=request.query_params.get("DeviceType"),
            language=request.query_params.get("language"),
            push_options=DEFAULT_PUSH_OPTIONS if is_handshake else None,
        )
    except Exception as exc:
        remark = f"device_registration_failed: {exc}"

    if is_attlog:
        if _device_records_attendance(context["device_sn"]):
            saved_count = _parse_and_save_attlog(context, body)
            _mark_raw_request_parsed(context["raw_request_id"])
            if saved_count > 0:
                _update_device_sync_state(context, "ATTLOG", _request_stamp(request))
        else:
            saved_count = 0
            _debug_log(
                "ATTLOG SKIPPED",
                {
                    "Device": context["device_sn"] or "",
                    "Reason": "record_attendance disabled",
                    "Raw Request ID": context["raw_request_id"],
                },
            )
        response_body = f"OK:{saved_count}"
        context["response_body"] = response_body
        _update_raw_request_response(context["raw_request_id"], response_body, response_status_code)

    if is_operlog:
        saved_count = _parse_and_save_operlog(context, body)
        _mark_raw_request_parsed(context["raw_request_id"])
        if saved_count > 0:
            _update_device_sync_state(context, "OPERLOG", _request_stamp(request))
        response_body = f"OK:{saved_count}"
        context["response_body"] = response_body
        _update_raw_request_response(context["raw_request_id"], response_body, response_status_code)

    _save_device_event(context, device_id, remark)
    _log_device_connection(
        context["device_sn"],
        context["client_ip"],
        context["received_at"],
        context["method"],
        context["url"],
        response_body,
        response_status_code,
    )
    if is_handshake:
        _log_initialization_completed(
            context["device_sn"],
            context["client_ip"],
            request.query_params.get("pushver"),
            response_body,
        )
    return PlainTextResponse(response_body, status_code=response_status_code, media_type="text/plain")


@router.get("/iclock/getrequest")
async def iclock_getrequest(request: Request) -> PlainTextResponse:
    response_body = "OK"
    response_status_code = 200
    body = await request.body()
    context = _save_raw_request(request, body, response_body, response_status_code)
    try:
        _upsert_device(context["device_sn"], context["client_ip"], context["received_at"])
    except Exception as exc:
        _debug_log(
            "ERROR",
            {
                "Device": context["device_sn"] or "",
                "Module": "DEVICE REGISTRATION",
                "Reason": exc,
            },
        )
    _debug_log(
        "HEARTBEAT",
        {
            "Device": context["device_sn"] or "",
            "Client IP": context["client_ip"] or "",
        },
    )
    return PlainTextResponse(response_body, status_code=response_status_code, media_type="text/plain")


@router.post("/iclock/devicecmd")
async def iclock_devicecmd(request: Request) -> PlainTextResponse:
    response_body = "OK"
    response_status_code = 200
    body = await request.body()
    context = _save_raw_request(request, body, response_body, response_status_code)
    try:
        _upsert_device(context["device_sn"], context["client_ip"], context["received_at"])
    except Exception as exc:
        _debug_log(
            "ERROR",
            {
                "Device": context["device_sn"] or "",
                "Module": "DEVICE REGISTRATION",
                "Reason": exc,
            },
        )
    return PlainTextResponse(response_body, status_code=response_status_code, media_type="text/plain")
