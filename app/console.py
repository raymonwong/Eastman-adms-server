from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import false, func, or_, text

from app.database import SessionLocal
from app.models import AttendanceEvent, Device, DeviceUser, OperationEvent, RawRequest

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

DUBAI_TZ = ZoneInfo("Asia/Dubai")
ALL_DEVICES_FILTER = "all"
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


def _device_name(device: Device | None, device_sn: str | None) -> str:
    if device is None:
        return "Unknown Device"
    return device.device_name or f"New Machine ({device.device_sn})"


def _device_display(device: Device | None, device_sn: str | None) -> str:
    name = _device_name(device, device_sn)
    sn = device.device_sn if device is not None else device_sn
    location = device.location if device is not None else None
    parts = [part for part in (name, sn, location) if part]
    return " · ".join(parts)


def _classify_device(last_seen: datetime | None) -> str:
    if last_seen is None:
        return "OFFLINE"
    age_seconds = (_utc_now_naive() - last_seen).total_seconds()
    return "ONLINE" if age_seconds <= OFFLINE_AFTER_SECONDS else "OFFLINE"


def _visible_devices(session) -> list[Device]:
    return (
        session.query(Device)
        .filter(Device.show_in_console.is_(True))
        .order_by(Device.updated_at.desc(), Device.device_name.asc(), Device.device_sn.asc())
        .all()
    )


def _device_filters(devices: list[Device]) -> list[dict[str, str]]:
    filters = [{"value": ALL_DEVICES_FILTER, "label": "All Devices / 所有设备"}]
    filters.extend({"value": f"device:{device.device_sn}", "label": _device_display(device, device.device_sn)} for device in devices)
    return filters


def _filter_devices(devices: list[Device], selected_filter: str | None) -> list[Device]:
    if not selected_filter or selected_filter == ALL_DEVICES_FILTER:
        return devices
    if selected_filter.startswith("device:"):
        device_sn = selected_filter.removeprefix("device:")
        return [device for device in devices if device.device_sn == device_sn]
    return devices


def _device_map(devices: list[Device]) -> dict[str, Device]:
    return {device.device_sn: device for device in devices}


def _device_sns(devices: list[Device]) -> list[str]:
    return [device.device_sn for device in devices]


def _device_filter(query, device_sns: list[str]):
    if not device_sns:
        return query.filter(false())
    return query.filter(RawRequest.device_sn.in_(device_sns))


def _attendance_filter(query, device_sns: list[str]):
    if not device_sns:
        return query.filter(false())
    return query.filter(AttendanceEvent.device_sn.in_(device_sns))


def _operation_filter(query, device_sns: list[str]):
    if not device_sns:
        return query.filter(false())
    return query.filter(OperationEvent.device_sn.in_(device_sns))


def _user_filter(query, device_sns: list[str]):
    if not device_sns:
        return query.filter(false())
    return query.filter(DeviceUser.device_sn.in_(device_sns))


def _latest_raw_request(session, device_sn: str | None = None) -> RawRequest | None:
    query = session.query(RawRequest)
    if device_sn is not None:
        query = query.filter(RawRequest.device_sn == device_sn)
    return query.order_by(RawRequest.received_at.desc(), RawRequest.id.desc()).first()


def _latest_data_upload(session, device_sn: str | None = None) -> datetime | None:
    query = session.query(func.max(RawRequest.received_at)).filter(RawRequest.request_path == "/iclock/cdata")
    if device_sn is not None:
        query = query.filter(RawRequest.device_sn == device_sn)
    return query.filter(or_(RawRequest.query_string.ilike("%table=ATTLOG%"), RawRequest.query_string.ilike("%table=OPERLOG%"))).scalar()


def _latest_heartbeat(session, device_sn: str) -> datetime | None:
    return (
        session.query(func.max(RawRequest.received_at))
        .filter(RawRequest.device_sn == device_sn, RawRequest.request_path == "/iclock/getrequest")
        .scalar()
    )


def _request_type(raw_request: RawRequest | None) -> str:
    if raw_request is None:
        return "-"

    query_string = raw_request.query_string or ""
    body = (raw_request.body or "").strip()
    upper_query = query_string.upper()

    if raw_request.request_path == "/iclock/getrequest":
        return "HEARTBEAT"
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
            return "USER" if record_type == "USER" else "OPLOG"
        return "CDATA"
    return (raw_request.request_path or "UNKNOWN").strip("/").upper() or "UNKNOWN"


def _parse_user_details(line: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for field in line.split()[1:]:
        if "=" not in field:
            continue
        key, value = field.split("=", 1)
        if key:
            values[key] = value
    return values


def _event(
    event_type: str,
    event_time: datetime | None,
    device: Device | None,
    device_sn: str | None,
    details: dict[str, object],
) -> dict[str, object]:
    return {
        "type": event_type,
        "time": _short_time(event_time),
        "time_full": _format_dubai(event_time),
        "device_name": _device_name(device, device_sn),
        "device_display": _device_display(device, device_sn),
        "device_sn": device_sn or "",
        "details": details,
    }


def _raw_event(raw_request: RawRequest, device_map: dict[str, Device]) -> dict[str, object] | None:
    query_string = raw_request.query_string or ""
    body = (raw_request.body or "").strip()
    upper_query = query_string.upper()
    device = device_map.get(raw_request.device_sn or "")

    if raw_request.request_path == "/iclock/getrequest":
        return _event("HEARTBEAT", raw_request.received_at, device, raw_request.device_sn, {"Client IP": raw_request.client_ip or ""})
    if "OPTIONS=ALL" in upper_query:
        return _event("HANDSHAKE", raw_request.received_at, device, raw_request.device_sn, {"Client IP": raw_request.client_ip or ""})
    if "TABLE=ATTLOG" in upper_query:
        first_line = body.splitlines()[0] if body else ""
        fields = first_line.split("\t")
        return _event(
            "ATTLOG",
            raw_request.received_at,
            device,
            raw_request.device_sn,
            {
                "PIN": fields[0] if fields else "",
                "Attendance Time": fields[1] if len(fields) > 1 else "",
            },
        )
    if "TABLE=OPERLOG" in upper_query:
        first_line = body.splitlines()[0] if body else ""
        record_type = first_line.split(None, 1)[0].upper() if first_line else "OPLOG"
        if record_type == "USER":
            details = _parse_user_details(first_line)
            return _event("USER", raw_request.received_at, device, raw_request.device_sn, {"PIN": details.get("PIN", ""), "User Name": details.get("Name", "")})
        return _event("OPLOG", raw_request.received_at, device, raw_request.device_sn, {"Details": first_line})
    return None


def _dashboard(session, devices: list[Device]) -> dict[str, int]:
    today_start = _today_start_utc_naive()
    device_sns = _device_sns(devices)
    online = 0
    offline = 0

    for device in devices:
        if _classify_device(_latest_heartbeat(session, device.device_sn)) == "ONLINE":
            online += 1
        else:
            offline += 1

    attendance_query = session.query(AttendanceEvent).filter(AttendanceEvent.receive_time >= today_start)
    user_query = session.query(DeviceUser).filter(DeviceUser.receive_time >= today_start)
    operation_query = session.query(OperationEvent).filter(OperationEvent.receive_time >= today_start)

    return {
        "online_devices": online,
        "offline_devices": offline,
        "attendance": _attendance_filter(attendance_query, device_sns).count(),
        "user": _user_filter(user_query, device_sns).count(),
        "oplog": _operation_filter(operation_query, device_sns).count(),
    }


def _exception_overview(device_summary: list[dict[str, object]], latest_activity: list[dict[str, object]]) -> dict[str, object]:
    offline_devices = [row for row in device_summary if row.get("status") == "OFFLINE"]
    latest_offline_time = "-"
    offline_times = [row.get("last_heartbeat") for row in offline_devices if row.get("last_heartbeat") and row.get("last_heartbeat") != "-"]
    if offline_times:
        latest_offline_time = max(str(value) for value in offline_times)

    return {
        "offline_devices": len(offline_devices),
        "heartbeat_timeout_devices": len(offline_devices),
        "last_exception_time": latest_offline_time,
        "last_normal_attendance_time": latest_activity[0]["attendance_time"] if latest_activity else "-",
    }


def _heartbeat_summary(session, devices: list[Device]) -> dict[str, object]:
    device_sns = _device_sns(devices)
    query = session.query(RawRequest).filter(RawRequest.request_path == "/iclock/getrequest")
    query = _device_filter(query, device_sns)
    latest = query.order_by(RawRequest.received_at.desc(), RawRequest.id.desc()).first()
    return {
        "count": query.count(),
        "last_time": _format_dubai(latest.received_at) if latest is not None else "-",
        "last_device": _device_display(_device_map(devices).get(latest.device_sn if latest else ""), latest.device_sn if latest else ""),
        "last_client_ip": latest.client_ip if latest is not None else "-",
    }


def _attendance_status_label(status: str | None) -> str:
    if status is None or status == "":
        return "Unknown / 未知"
    if status == "255":
        return "Unrecognized Attendance Status / 未识别的考勤状态"
    return status


def _latest_activities(session, devices: list[Device]) -> list[dict[str, object]]:
    device_sns = _device_sns(devices)
    devices_by_sn = _device_map(devices)
    attendance_events = (
        _attendance_filter(session.query(AttendanceEvent), device_sns)
        .order_by(AttendanceEvent.attendance_time.desc(), AttendanceEvent.id.desc())
        .limit(7)
        .all()
    )
    user_names = {
        (user.device_sn, user.pin): user.name
        for user in _user_filter(session.query(DeviceUser), device_sns).all()
    }

    return [
        {
            "device_name": _device_name(devices_by_sn.get(item.device_sn), item.device_sn),
            "device_display": _device_display(devices_by_sn.get(item.device_sn), item.device_sn),
            "device_sn": item.device_sn,
            "employee_pin": item.pin,
            "employee_name": user_names.get((item.device_sn, item.pin)) or "-",
            "attendance_type": _attendance_status_label(item.status),
            "raw_status": item.status or "",
            "attendance_time": _format_dubai(item.attendance_time, source="local"),
            "receive_time": _format_dubai(item.receive_time),
        }
        for item in attendance_events
    ]


def _events(session, devices: list[Device]) -> list[dict[str, object]]:
    device_sns = _device_sns(devices)
    devices_by_sn = _device_map(devices)
    events: list[dict[str, object]] = []

    attendance_events = (
        _attendance_filter(session.query(AttendanceEvent), device_sns)
        .order_by(AttendanceEvent.receive_time.desc(), AttendanceEvent.id.desc())
        .limit(10)
        .all()
    )
    saved_attlog_raw_ids = {item.raw_request_id for item in attendance_events if item.raw_request_id is not None}

    for device in devices:
        last_heartbeat = _latest_heartbeat(session, device.device_sn)
        status = _classify_device(last_heartbeat)
        events.append(
            _event(
                "DEVICE ONLINE" if status == "ONLINE" else "DEVICE OFFLINE",
                last_heartbeat or device.updated_at,
                device,
                device.device_sn,
                {"Status": status, "Last Heartbeat": _format_dubai(last_heartbeat)},
            )
        )

    raw_requests = (
        _device_filter(
            session.query(RawRequest).filter(or_(RawRequest.request_path == "/iclock/getrequest", RawRequest.request_path == "/iclock/cdata")),
            device_sns,
        )
        .order_by(RawRequest.received_at.desc(), RawRequest.id.desc())
        .limit(40)
        .all()
    )
    for raw_request in raw_requests:
        # Hide raw ATTLOG rows when the parsed attendance event is already shown.
        if raw_request.id in saved_attlog_raw_ids and "TABLE=ATTLOG" in (raw_request.query_string or "").upper():
            continue
        event = _raw_event(raw_request, devices_by_sn)
        if event is not None:
            events.append(event)

    for item in attendance_events:
        device = devices_by_sn.get(item.device_sn)
        events.append(
            _event(
                "ATTLOG SAVED",
                item.receive_time,
                device,
                item.device_sn,
                {
                    "Attendance ID": item.id,
                    "PIN": item.pin,
                    "Attendance Time": _format_dubai(item.attendance_time, source="local"),
                },
            )
        )

    operation_events = (
        _operation_filter(session.query(OperationEvent), device_sns)
        .order_by(OperationEvent.receive_time.desc(), OperationEvent.id.desc())
        .limit(10)
        .all()
    )
    for item in operation_events:
        device = devices_by_sn.get(item.device_sn)
        events.append(
            _event(
                "OPLOG SAVED",
                item.receive_time,
                device,
                item.device_sn,
                {"Operation": item.operation_code, "Operation Time": _format_dubai(item.operation_time, source="local")},
            )
        )

    users = (
        _user_filter(session.query(DeviceUser), device_sns)
        .order_by(DeviceUser.receive_time.desc(), DeviceUser.id.desc())
        .limit(10)
        .all()
    )
    for user in users:
        device = devices_by_sn.get(user.device_sn)
        events.append(_event("USER SAVED", user.receive_time, device, user.device_sn, {"PIN": user.pin, "User Name": user.name or ""}))

    events.sort(key=lambda item: item["time_full"], reverse=True)
    return events[:10]


def _device_summary(session, devices: list[Device]) -> list[dict[str, object]]:
    today_start = _today_start_utc_naive()
    rows: list[dict[str, object]] = []

    for device in devices:
        last_heartbeat = _latest_heartbeat(session, device.device_sn)
        last_attendance = (
            session.query(func.max(AttendanceEvent.receive_time))
            .filter(AttendanceEvent.device_sn == device.device_sn)
            .scalar()
        )
        today_attendance = (
            session.query(AttendanceEvent)
            .filter(AttendanceEvent.device_sn == device.device_sn, AttendanceEvent.receive_time >= today_start)
            .count()
        )
        rows.append(
            {
                "device_name": _device_name(device, device.device_sn),
                "device_display": _device_display(device, device.device_sn),
                "device_sn": device.device_sn,
                "location": device.location or "-",
                "status": _classify_device(last_heartbeat),
                "last_heartbeat": _format_dubai(last_heartbeat),
                "last_heartbeat_sort": _format_dubai(last_heartbeat),
                "last_attendance": _format_dubai(last_attendance),
                "last_attendance_sort": _format_dubai(last_attendance),
                "today_attendance": today_attendance,
                "record_attendance": bool(device.record_attendance),
                "show_in_console": bool(device.show_in_console),
            }
        )

    return rows


def _console_data(selected_filter: str | None = None) -> dict[str, object]:
    database_status = "Connected"
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
            visible_devices = _visible_devices(session)
            active_filter = selected_filter if selected_filter in {item["value"] for item in _device_filters(visible_devices)} else ALL_DEVICES_FILTER
            filtered_devices = _filter_devices(visible_devices, active_filter)
            filters = _device_filters(visible_devices)
            dashboard = _dashboard(session, filtered_devices)
            events = _events(session, filtered_devices)
            heartbeat_summary = _heartbeat_summary(session, filtered_devices)
            latest_activity = _latest_activities(session, filtered_devices)
            device_summary = _device_summary(session, filtered_devices)
            exception_overview = _exception_overview(device_summary, latest_activity)
    except Exception as exc:
        database_status = f"Error: {exc}"
        active_filter = ALL_DEVICES_FILTER
        filters = [{"value": ALL_DEVICES_FILTER, "label": "All Devices / 所有设备"}]
        dashboard = {"online_devices": 0, "offline_devices": 0, "attendance": 0, "user": 0, "oplog": 0}
        heartbeat_summary = {"count": 0, "last_time": "-", "last_device": "-", "last_client_ip": "-"}
        events = [_event("ERROR", _utc_now_naive(), None, "", {"Module": "CONSOLE", "Reason": str(exc)})]
        latest_activity = []
        device_summary = []
        exception_overview = {"offline_devices": 0, "heartbeat_timeout_devices": 0, "last_exception_time": "-", "last_normal_attendance_time": "-"}

    return {
        "server": {
            "server": "Running",
            "database": database_status,
            "api": "Normal",
            "server_time": _dubai_now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "filter": {
            "selected": active_filter,
            "options": filters,
        },
        "dashboard": dashboard,
        "exception_overview": exception_overview,
        "heartbeat_summary": heartbeat_summary,
        "latest_activity": latest_activity,
        "events": events,
        "device_summary": device_summary,
    }


@router.get("/console", response_class=HTMLResponse)
async def console(request: Request, format: str | None = None, device_filter: str | None = None):
    data = _console_data(device_filter)
    if format == "json":
        return JSONResponse(data)
    return templates.TemplateResponse("console.html", {"request": request, "data": data})
