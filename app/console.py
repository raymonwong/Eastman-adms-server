from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_, text

from app.database import SessionLocal
from app.models import AttendanceEvent, Device, DeviceUser, OperationEvent, RawRequest

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

DUBAI_TZ = ZoneInfo("Asia/Dubai")
OFFLINE_AFTER_SECONDS = 60


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _dubai_now() -> datetime:
    return datetime.now(DUBAI_TZ)


def _today_start_utc_naive() -> datetime:
    dubai_start = _dubai_now().replace(hour=0, minute=0, second=0, microsecond=0)
    return dubai_start.astimezone(UTC).replace(tzinfo=None)


def _format_dubai(value: datetime | None, *, source: str = "utc") -> str:
    if value is None:
        return "-"
    if source == "utc":
        return value.replace(tzinfo=UTC).astimezone(DUBAI_TZ).strftime("%Y-%m-%d %H:%M:%S")
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _short_time(value: datetime | None, *, source: str = "utc") -> str:
    formatted = _format_dubai(value, source=source)
    return "-" if formatted == "-" else formatted[-8:]


def _classify_device(last_seen: datetime | None) -> str:
    if last_seen is None:
        return "OFFLINE"
    age_seconds = (_utc_now_naive() - last_seen).total_seconds()
    if age_seconds <= OFFLINE_AFTER_SECONDS:
        return "ONLINE"
    return "OFFLINE"


def _event(event_type: str, event_time: datetime | None, device_sn: str | None, details: dict[str, object]) -> dict[str, object]:
    return {
        "type": event_type,
        "time": _short_time(event_time),
        "time_full": _format_dubai(event_time),
        "device_sn": device_sn or "",
        "details": details,
    }


def _latest_raw_event(raw_request: RawRequest) -> dict[str, object] | None:
    query_string = raw_request.query_string or ""
    body = (raw_request.body or "").strip()
    upper_query = query_string.upper()

    if raw_request.request_path == "/iclock/getrequest":
        return _event("HEARTBEAT", raw_request.received_at, raw_request.device_sn, {"Client IP": raw_request.client_ip or ""})
    if "OPTIONS=ALL" in upper_query:
        return _event("HANDSHAKE", raw_request.received_at, raw_request.device_sn, {"Client IP": raw_request.client_ip or ""})
    if "TABLE=ATTLOG" in upper_query:
        first_line = body.splitlines()[0] if body else ""
        fields = first_line.split("\t")
        return _event(
            "ATTLOG RECEIVED",
            raw_request.received_at,
            raw_request.device_sn,
            {
                "PIN": fields[0] if fields else "",
                "Attendance Time": fields[1] if len(fields) > 1 else "",
            },
        )
    if "TABLE=OPERLOG" in upper_query:
        first_line = body.splitlines()[0] if body else ""
        record_type = first_line.split(None, 1)[0].upper() if first_line else "OPERLOG"
        if record_type == "USER":
            details = _parse_user_details(first_line)
            return _event(
                "USER RECEIVED",
                raw_request.received_at,
                raw_request.device_sn,
                {"PIN": details.get("PIN", ""), "User Name": details.get("Name", "")},
            )
        return _event("OPERLOG RECEIVED", raw_request.received_at, raw_request.device_sn, {"Body": first_line})
    return None


def _request_type(raw_request: RawRequest | None) -> str:
    if raw_request is None:
        return "-"

    query_string = raw_request.query_string or ""
    body = (raw_request.body or "").strip()
    upper_query = query_string.upper()

    if raw_request.request_path == "/iclock/getrequest":
        return "GETREQUEST"
    if raw_request.request_path == "/iclock/devicecmd":
        return "DEVICECMD"
    if raw_request.request_path == "/iclock/cdata":
        if "OPTIONS=ALL" in upper_query:
            return "HANDSHAKE"
        if "TABLE=ATTLOG" in upper_query:
            return "ATTLOG"
        if "TABLE=OPERLOG" in upper_query:
            first_line = body.splitlines()[0] if body else ""
            record_type = first_line.split(None, 1)[0].upper() if first_line else ""
            return "USER" if record_type == "USER" else "OPERLOG"
        return "CDATA"
    return (raw_request.request_path or "UNKNOWN").strip("/").upper() or "UNKNOWN"


def _latest_raw_request(session, device_sn: str | None = None) -> RawRequest | None:
    query = session.query(RawRequest)
    if device_sn is not None:
        query = query.filter(RawRequest.device_sn == device_sn)
    return query.order_by(RawRequest.received_at.desc(), RawRequest.id.desc()).first()


def _latest_data_upload(session, device_sn: str | None = None) -> datetime | None:
    query = session.query(func.max(RawRequest.received_at)).filter(RawRequest.request_path == "/iclock/cdata")
    if device_sn is not None:
        query = query.filter(RawRequest.device_sn == device_sn)
    return query.filter(
        or_(
            RawRequest.query_string.ilike("%table=ATTLOG%"),
            RawRequest.query_string.ilike("%table=OPERLOG%"),
        )
    ).scalar()


def _parse_user_details(line: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for field in line.split()[1:]:
        if "=" not in field:
            continue
        key, value = field.split("=", 1)
        if key:
            values[key] = value
    return values


def _device_cards(session) -> list[dict[str, object]]:
    devices = session.query(Device).order_by(Device.device_sn.asc()).all()
    cards: list[dict[str, object]] = []

    for device in devices:
        latest_raw = _latest_raw_request(session, device.device_sn)
        last_seen = latest_raw.received_at if latest_raw is not None else None
        last_heartbeat = (
            session.query(func.max(RawRequest.received_at))
            .filter(RawRequest.device_sn == device.device_sn, RawRequest.request_path == "/iclock/getrequest")
            .scalar()
        )
        last_data_upload = _latest_data_upload(session, device.device_sn)
        last_attlog = (
            session.query(func.max(AttendanceEvent.receive_time))
            .filter(AttendanceEvent.device_sn == device.device_sn)
            .scalar()
        )
        last_operlog = (
            session.query(func.max(OperationEvent.receive_time))
            .filter(OperationEvent.device_sn == device.device_sn)
            .scalar()
        )
        last_user = (
            session.query(func.max(DeviceUser.receive_time))
            .filter(DeviceUser.device_sn == device.device_sn)
            .scalar()
        )
        status = _classify_device(last_seen)
        cards.append(
            {
                "device_sn": device.device_sn,
                "status": status,
                "last_seen": _format_dubai(last_seen),
                "last_heartbeat": _format_dubai(last_heartbeat),
                "last_data_upload": _format_dubai(last_data_upload),
                "last_request": _request_type(latest_raw),
                "last_raw_request_id": latest_raw.id if latest_raw is not None else "-",
                "last_attlog": _format_dubai(last_attlog),
                "last_operlog": _format_dubai(last_operlog),
                "last_user": _format_dubai(last_user),
                "client_ip": (latest_raw.client_ip if latest_raw is not None and latest_raw.client_ip else device.ip_address) or "-",
                "push_version": device.push_version or "-",
            }
        )

    return cards


def _events(session) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    raw_requests = (
        session.query(RawRequest)
        .filter(
            or_(
                RawRequest.request_path == "/iclock/getrequest",
                RawRequest.request_path == "/iclock/cdata",
            )
        )
        .order_by(RawRequest.received_at.desc())
        .limit(80)
        .all()
    )
    for raw_request in raw_requests:
        event = _latest_raw_event(raw_request)
        if event is not None:
            events.append(event)

    attendance_events = session.query(AttendanceEvent).order_by(AttendanceEvent.receive_time.desc()).limit(30).all()
    for item in attendance_events:
        events.append(
            _event(
                "ATTLOG SAVED",
                item.receive_time,
                item.device_sn,
                {
                    "Attendance ID": item.id,
                    "Raw Request ID": item.raw_request_id,
                    "PIN": item.pin,
                    "Attendance Time": _format_dubai(item.attendance_time, source="local"),
                },
            )
        )

    operation_events = session.query(OperationEvent).order_by(OperationEvent.receive_time.desc()).limit(30).all()
    for item in operation_events:
        events.append(
            _event(
                "OPERLOG SAVED",
                item.receive_time,
                item.device_sn,
                {"Operation ID": item.id, "Operation": item.operation_code, "Operation Time": _format_dubai(item.operation_time, source="local")},
            )
        )

    users = session.query(DeviceUser).order_by(DeviceUser.receive_time.desc()).limit(30).all()
    for user in users:
        events.append(_event("USER SAVED", user.receive_time, user.device_sn, {"User ID": user.id, "PIN": user.pin, "User Name": user.name or ""}))

    events.sort(key=lambda item: item["time_full"], reverse=True)
    return events[:80]


def _statistics(session) -> dict[str, int]:
    today_start = _today_start_utc_naive()
    return {
        "heartbeat": session.query(RawRequest).filter(RawRequest.request_path == "/iclock/getrequest", RawRequest.received_at >= today_start).count(),
        "attlog": session.query(AttendanceEvent).filter(AttendanceEvent.receive_time >= today_start).count(),
        "operlog": session.query(OperationEvent).filter(OperationEvent.receive_time >= today_start).count(),
        "user": session.query(DeviceUser).filter(DeviceUser.receive_time >= today_start).count(),
    }


def _latest_activity(session) -> dict[str, object]:
    latest_attendance = session.query(AttendanceEvent).order_by(AttendanceEvent.receive_time.desc()).first()
    if latest_attendance is None:
        return {"latest_attendance": None}
    return {
        "latest_attendance": {
            "pin": latest_attendance.pin,
            "attendance_time": _format_dubai(latest_attendance.attendance_time, source="local"),
            "receive_time": _format_dubai(latest_attendance.receive_time),
            "status": latest_attendance.status or "-",
        }
    }


def _console_data() -> dict[str, object]:
    database_status = "Connected"
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
            devices = _device_cards(session)
            events = _events(session)
            statistics = _statistics(session)
            latest_activity = _latest_activity(session)
            latest_raw = _latest_raw_request(session)
            last_data_upload = _latest_data_upload(session)
    except Exception as exc:
        database_status = f"Error: {exc}"
        devices = []
        events = [_event("ERROR", _utc_now_naive(), "", {"Module": "CONSOLE", "Reason": str(exc)})]
        statistics = {"heartbeat": 0, "attlog": 0, "operlog": 0, "user": 0}
        latest_activity = {"latest_attendance": None}
        latest_raw = None
        last_data_upload = None

    online_devices = [device for device in devices if device["status"] == "ONLINE"]
    warning_devices = [device for device in devices if device["status"] == "WARNING"]
    last_seen = "-"
    last_seen_times = [device["last_seen"] for device in devices if device["last_seen"] != "-"]
    if last_seen_times:
        last_seen = max(last_seen_times)
    last_heartbeat = "-"
    heartbeat_times = [device["last_heartbeat"] for device in devices if device["last_heartbeat"] != "-"]
    if heartbeat_times:
        last_heartbeat = max(heartbeat_times)

    if online_devices:
        headline = {"status": "ONLINE", "text": "DEVICE ONLINE", "last_seen": last_seen}
    elif warning_devices:
        headline = {"status": "WARNING", "text": "DEVICE WARNING", "last_seen": last_seen}
    else:
        headline = {"status": "OFFLINE", "text": "DEVICE OFFLINE", "last_seen": last_seen}

    summary = {
        "server": "Running",
        "device": headline["status"],
        "last_seen": last_seen,
        "last_heartbeat": last_heartbeat,
        "last_data_upload": _format_dubai(last_data_upload),
        "last_raw_request": latest_raw.id if latest_raw is not None else "-",
        "last_request": _request_type(latest_raw),
    }

    return {
        "server": {
            "server": "Running",
            "database": database_status,
            "api": "Normal",
            "server_time": _dubai_now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "headline": headline,
        "summary": summary,
        "devices": devices,
        "events": events,
        "statistics": statistics,
        "latest_activity": latest_activity,
    }


@router.get("/console", response_class=HTMLResponse)
async def console(request: Request, format: str | None = None):
    data = _console_data()
    if format == "json":
        return JSONResponse(data)
    return templates.TemplateResponse("console.html", {"request": request, "data": data})
