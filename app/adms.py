import hashlib
import json
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models import AttendanceEvent, Device, DeviceEventLog, RawRequest

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
                ip_address=ip_address,
                first_online=received_at,
                last_online=received_at,
                status="online",
            )
            session.add(device)
        else:
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


def _is_initialization_handshake(request: Request) -> bool:
    return request.method == "GET" and request.query_params.get("options", "").lower() == "all"


def _is_attlog_upload(request: Request) -> bool:
    return request.method == "POST" and request.query_params.get("table", "").upper() == "ATTLOG"


def _build_initialization_response(device_sn: str | None) -> str:
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
    print("---------------------------------------", flush=True)
    print("Device Connected", flush=True)
    print(f"Time: {received_at.isoformat()}", flush=True)
    print(f"SN: {device_sn or ''}", flush=True)
    print(f"IP: {client_ip or ''}", flush=True)
    print(f"Method: {method}", flush=True)
    print(f"URL: {url}", flush=True)
    print(f"Response: {response_body}", flush=True)
    print(f"Status: {response_status_code}", flush=True)
    print("---------------------------------------", flush=True)


def _log_initialization_completed(
    device_sn: str | None,
    push_version: str | None,
    device_type: str | None,
    language: str | None,
) -> None:
    print("---------------------------------------", flush=True)
    print("Initialization Completed", flush=True)
    print(f"SN: {device_sn or ''}", flush=True)
    print(f"Push Version: {push_version or ''}", flush=True)
    print(f"Device Type: {device_type or ''}", flush=True)
    print(f"Language: {language or ''}", flush=True)
    print(f"TimeZone: {DUBAI_TIMEZONE}", flush=True)
    print(f"Realtime: {DEFAULT_REALTIME}", flush=True)
    print(f"Delay: {DEFAULT_DELAY}", flush=True)
    print(f"TransFlag: {DEFAULT_TRANS_FLAG}", flush=True)
    print("---------------------------------------", flush=True)


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
        if not line:
            continue
        try:
            event = _parse_attlog_line(
                line,
                context["device_sn"],
                context["received_at"],
                context["raw_request_id"],
            )
        except Exception as exc:
            print("---------------------------------------", flush=True)
            print("ATTLOG Parse Failed", flush=True)
            print(f"Device SN: {context['device_sn'] or ''}", flush=True)
            print(f"Line: {line_number}", flush=True)
            print(f"Error: {exc}", flush=True)
            print("---------------------------------------", flush=True)
            continue

        if not _save_attendance_event(event):
            continue

        saved_count += 1
        print("---------------------------------------", flush=True)
        print("ATTLOG Parsed", flush=True)
        print(f"Device SN: {event.device_sn}", flush=True)
        print(f"Record Count: {saved_count}", flush=True)
        print(f"PIN: {event.pin}", flush=True)
        print(f"Attendance Time: {event.attendance_time}", flush=True)
        print("---------------------------------------", flush=True)

    return saved_count


@router.api_route("/iclock/cdata", methods=["GET", "POST"])
async def iclock_cdata(request: Request) -> PlainTextResponse:
    device_sn = request.query_params.get("SN") or request.query_params.get("sn")
    is_handshake = _is_initialization_handshake(request)
    is_attlog = _is_attlog_upload(request)
    response_body = _build_initialization_response(device_sn) if is_handshake else "OK"
    response_status_code = 200
    body = await request.body()
    context = _save_raw_request(request, body, response_body, response_status_code)

    if is_attlog:
        saved_count = _parse_and_save_attlog(context, body)
        response_body = f"OK:{saved_count}"
        context["response_body"] = response_body
        _update_raw_request_response(context["raw_request_id"], response_body, response_status_code)

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
            request.query_params.get("pushver"),
            request.query_params.get("DeviceType"),
            request.query_params.get("language"),
        )
    return PlainTextResponse(response_body, status_code=response_status_code, media_type="text/plain")


@router.get("/iclock/getrequest")
async def iclock_getrequest(request: Request) -> PlainTextResponse:
    response_body = "OK"
    response_status_code = 200
    body = await request.body()
    _save_raw_request(request, body, response_body, response_status_code)
    return PlainTextResponse(response_body, status_code=response_status_code, media_type="text/plain")


@router.post("/iclock/devicecmd")
async def iclock_devicecmd(request: Request) -> PlainTextResponse:
    response_body = "OK"
    response_status_code = 200
    body = await request.body()
    _save_raw_request(request, body, response_body, response_status_code)
    return PlainTextResponse(response_body, status_code=response_status_code, media_type="text/plain")
