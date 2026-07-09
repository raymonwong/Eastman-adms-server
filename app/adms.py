import hashlib
import json
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app.database import SessionLocal
from app.models import Device, DeviceEventLog, RawRequest

router = APIRouter()


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


def _upsert_device(device_sn: str | None, ip_address: str | None, received_at: datetime) -> int | None:
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
        session.commit()
        return device.id


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
        session.commit()

    return {
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


@router.api_route("/iclock/cdata", methods=["GET", "POST"])
async def iclock_cdata(request: Request) -> PlainTextResponse:
    response_body = "OK"
    response_status_code = 200
    body = await request.body()
    context = _save_raw_request(request, body, response_body, response_status_code)

    device_id = None
    remark = None
    try:
        device_id = _upsert_device(context["device_sn"], context["client_ip"], context["received_at"])
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
    return PlainTextResponse(response_body, status_code=response_status_code)
