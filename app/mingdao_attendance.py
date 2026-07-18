from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
import os
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request as UrlRequest, urlopen

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.integration_config import get_config_value
from app.models import AttendanceEvent, AttendanceMingdaoSync, Device, DeviceUser


ATTENDANCE_SYNC_LOCK = Lock()
DEFAULT_BATCH_SIZE = 50
MAX_BATCH_SIZE = 200
SYNC_STATUSES = {"PENDING", "SYNCING", "SYNCED", "FAILED"}


class AttendanceSyncConfigError(ValueError):
    pass


class MissingEmployeeRecordID(ValueError):
    pass


def _env_bool(key: str, default: bool = False) -> bool:
    value = get_config_value(key, str(default)).strip().lower()
    return value in {"1", "true", "yes", "on", "enabled"}


def attendance_auto_sync_interval_seconds() -> int:
    raw_value = os.getenv("MINGDAO_ATTENDANCE_AUTO_SYNC_INTERVAL_SECONDS", "10").strip() or "10"
    try:
        interval = int(raw_value)
    except ValueError:
        interval = 10
    return max(5, min(interval, 3600))


def _required_env(key: str, label: str) -> str:
    value = get_config_value(key, "").strip()
    if not value:
        raise AttendanceSyncConfigError(f"{label} is not configured.")
    return value


def _attendance_rows_url(openapi_url: str, worksheet_id: str) -> str:
    cleaned_url = openapi_url.rstrip("/")
    encoded_worksheet_id = quote(worksheet_id.strip(), safe="")
    if "{worksheet_id}" in cleaned_url:
        resolved = cleaned_url.replace("{worksheet_id}", encoded_worksheet_id)
    elif "/v3/app/worksheets/" in cleaned_url:
        resolved = cleaned_url
    else:
        resolved = f"{cleaned_url}/v3/app/worksheets/{encoded_worksheet_id}"
    return resolved if resolved.endswith("/rows") else f"{resolved.rstrip('/')}/rows"


def _attendance_config() -> dict[str, str | bool]:
    if not _env_bool("MINGDAO_ATTENDANCE_SYNC_ENABLED"):
        raise AttendanceSyncConfigError("Attendance synchronization is disabled.")
    openapi_url = _required_env("MINGDAO_ATTENDANCE_OPENAPI_URL", "Mingdao Attendance OpenAPI URL")
    worksheet_id = _required_env("MINGDAO_ATTENDANCE_WORKSHEET_ID", "Worksheet ID")
    return {
        "enabled": True,
        "openapi_url": openapi_url,
        "app_key": _required_env("MINGDAO_ATTENDANCE_APP_KEY", "AppKey"),
        "sign": _required_env("MINGDAO_ATTENDANCE_SIGN", "Sign"),
        "worksheet_id": worksheet_id,
        "rows_url": _attendance_rows_url(openapi_url, worksheet_id),
        "employee_record_id_field_id": _required_env(
            "MINGDAO_ATTENDANCE_FIELD_EMPLOYEE_RECORD_ID",
            "Employee Record ID field ID",
        ),
        "check_time_field_id": _required_env("MINGDAO_ATTENDANCE_FIELD_CHECK_TIME", "Check Time field ID"),
        "device_name_field_id": _required_env("MINGDAO_ATTENDANCE_FIELD_DEVICE_NAME", "Device Name field ID"),
        "device_sn_field_id": _required_env("MINGDAO_ATTENDANCE_FIELD_DEVICE_SN", "Device SN field ID"),
        "retry_failed_after_minutes": int(get_config_value("MINGDAO_ATTENDANCE_RETRY_FAILED_AFTER_MINUTES", "60").strip() or "60"),
    }


def _format_datetime(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _extract_row_id(response_json: object) -> str | None:
    if isinstance(response_json, dict):
        direct = response_json.get("id") or response_json.get("rowId") or response_json.get("row_id")
        if direct:
            return str(direct)
        data = response_json.get("data")
        if isinstance(data, dict):
            return _extract_row_id(data)
        if isinstance(data, list) and data:
            return _extract_row_id(data[0])
    return None


def _find_mingdao_user(session: Session, pin: str) -> DeviceUser | None:
    return (
        session.execute(
            select(DeviceUser)
            .where(
                DeviceUser.pin == pin,
                DeviceUser.employee_id.is_not(None),
                DeviceUser.employee_id != "",
            )
            .order_by(DeviceUser.updated_at.desc())
        )
        .scalars()
        .first()
    )


def _device_name(session: Session, device_sn: str) -> str:
    device = session.execute(select(Device).where(Device.device_sn == device_sn)).scalars().first()
    if not device:
        return device_sn
    return device.device_name or device.device_sn


def _build_mingdao_payload(session: Session, event: AttendanceEvent, config: dict[str, str | bool]) -> dict[str, object]:
    user = _find_mingdao_user(session, event.pin)
    if not user or not user.employee_record_id:
        raise MissingEmployeeRecordID(f"Waiting for Mingdao employee_record_id for PIN {event.pin}.")

    return {
        "triggerWorkflow": True,
        "fields": [
            {
                "id": str(config["employee_record_id_field_id"]),
                "value": user.employee_record_id,
            },
            {
                "id": str(config["check_time_field_id"]),
                "value": _format_datetime(event.attendance_time),
            },
            {
                "id": str(config["device_name_field_id"]),
                "value": _device_name(session, event.device_sn),
            },
            {
                "id": str(config["device_sn_field_id"]),
                "value": event.device_sn,
            },
        ],
    }


def _post_mingdao_row(payload: dict[str, object], config: dict[str, str | bool]) -> tuple[int, str, dict[str, object]]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = UrlRequest(
        str(config["rows_url"]),
        data=body,
        headers={
            "HAP-Appkey": str(config["app_key"]),
            "HAP-Sign": str(config["sign"]),
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=15) as response:
        response_body = response.read().decode("utf-8", errors="replace")
        try:
            response_json = json.loads(response_body)
        except json.JSONDecodeError:
            response_json = {"success": False, "error_msg": "Mingdao response is not JSON."}
        return response.status, response_body, response_json


def create_missing_attendance_sync_records(session: Session, limit: int | None = None) -> int:
    query = (
        select(AttendanceEvent.id)
        .outerjoin(AttendanceMingdaoSync, AttendanceMingdaoSync.attendance_event_id == AttendanceEvent.id)
        .where(AttendanceMingdaoSync.id.is_(None))
        .order_by(AttendanceEvent.id.asc())
    )
    if limit:
        query = query.limit(limit)
    event_ids = list(session.execute(query).scalars())
    created = 0
    for event_id in event_ids:
        session.add(AttendanceMingdaoSync(attendance_event_id=event_id, sync_status="PENDING"))
        created += 1
    if not created:
        return 0
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return 0
    return created


def attendance_sync_status_summary() -> dict[str, int]:
    with SessionLocal() as session:
        rows = session.execute(
            select(AttendanceMingdaoSync.sync_status, func.count(AttendanceMingdaoSync.id)).group_by(
                AttendanceMingdaoSync.sync_status
            )
        ).all()
        summary = {status: 0 for status in SYNC_STATUSES}
        for status, count in rows:
            summary[str(status)] = int(count)
        summary["TOTAL"] = sum(summary.values())
        return summary


def sync_pending_attendance_to_mingdao(*, limit: int = DEFAULT_BATCH_SIZE) -> dict[str, object]:
    limit = max(1, min(int(limit), MAX_BATCH_SIZE))
    if not ATTENDANCE_SYNC_LOCK.acquire(blocking=False):
        return {
            "success": False,
            "message": "Attendance synchronization is already running.",
            "created_pending": 0,
            "uploaded": 0,
            "failed": 0,
            "skipped": 0,
            "status": attendance_sync_status_summary(),
        }

    try:
        config = _attendance_config()
        with SessionLocal() as session:
            created_pending = create_missing_attendance_sync_records(session)
            retry_cutoff = datetime.now(UTC) - timedelta(minutes=int(config["retry_failed_after_minutes"]))
            sync_rows = list(
                session.execute(
                    select(AttendanceMingdaoSync)
                    .where(
                        or_(
                            AttendanceMingdaoSync.sync_status == "PENDING",
                            and_(
                                AttendanceMingdaoSync.sync_status == "FAILED",
                                or_(
                                    AttendanceMingdaoSync.last_sync_time.is_(None),
                                    AttendanceMingdaoSync.last_sync_time <= retry_cutoff,
                                ),
                            ),
                        )
                    )
                    .order_by(AttendanceMingdaoSync.id.asc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )

            uploaded = 0
            failed = 0
            skipped = 0
            details: list[dict[str, object]] = []

            for sync_row in sync_rows:
                event = session.get(AttendanceEvent, sync_row.attendance_event_id)
                if not event:
                    sync_row.sync_status = "FAILED"
                    sync_row.retry_count += 1
                    sync_row.last_error = f"attendance_event {sync_row.attendance_event_id} no longer exists."
                    sync_row.last_sync_time = datetime.now(UTC)
                    failed += 1
                    session.commit()
                    continue

                sync_row.sync_status = "SYNCING"
                sync_row.last_error = None
                sync_row.last_sync_time = datetime.now(UTC)
                session.commit()

                try:
                    payload = _build_mingdao_payload(session, event, config)
                    sync_row.request_payload = json.dumps(payload, ensure_ascii=False)
                    status_code, response_body, response_json = _post_mingdao_row(payload, config)
                    sync_row.response_body = response_body
                    if status_code != 200 or response_json.get("success") is False:
                        raise RuntimeError(response_json.get("error_msg") or response_json.get("message") or response_body)
                    sync_row.sync_status = "SYNCED"
                    sync_row.mingdao_row_id = _extract_row_id(response_json)
                    sync_row.last_sync_time = datetime.now(UTC)
                    uploaded += 1
                    details.append(
                        {
                            "attendance_event_id": event.id,
                            "status": "SYNCED",
                            "mingdao_row_id": sync_row.mingdao_row_id,
                        }
                    )
                except MissingEmployeeRecordID as exc:
                    sync_row.sync_status = "PENDING"
                    sync_row.last_error = str(exc)
                    sync_row.last_sync_time = datetime.now(UTC)
                    skipped += 1
                    details.append(
                        {
                            "attendance_event_id": event.id,
                            "status": "WAITING_EMPLOYEE_RECORD_ID",
                            "reason": sync_row.last_error,
                        }
                    )
                except HTTPError as exc:
                    body = exc.read().decode("utf-8", errors="replace")
                    sync_row.sync_status = "FAILED"
                    sync_row.retry_count += 1
                    sync_row.last_error = f"HTTP {exc.code}: {body or exc.reason}"
                    sync_row.last_sync_time = datetime.now(UTC)
                    sync_row.response_body = body
                    failed += 1
                    details.append(
                        {
                            "attendance_event_id": event.id,
                            "status": "FAILED",
                            "reason": sync_row.last_error,
                        }
                    )
                except (URLError, TimeoutError, Exception) as exc:
                    sync_row.sync_status = "FAILED"
                    sync_row.retry_count += 1
                    sync_row.last_error = str(exc)
                    sync_row.last_sync_time = datetime.now(UTC)
                    failed += 1
                    details.append(
                        {
                            "attendance_event_id": event.id,
                            "status": "FAILED",
                            "reason": sync_row.last_error,
                        }
                    )
                finally:
                    session.commit()

            skipped = max(0, len(sync_rows) - uploaded - failed)
            return {
                "success": failed == 0,
                "message": "Attendance synchronization completed." if failed == 0 else "Attendance synchronization completed with failures.",
                "created_pending": created_pending,
                "uploaded": uploaded,
                "failed": failed,
                "skipped": skipped,
                "retry_failed_after_minutes": int(config["retry_failed_after_minutes"]),
                "mingdao_write_mode": "create_row_only",
                "retry_policy": "New and pending records sync automatically. Failed records retry after the configured interval.",
                "duplicate_prevention": "SYNCED attendance_event.id values are never uploaded again.",
                "details": details,
                "status": attendance_sync_status_summary(),
            }
    except AttendanceSyncConfigError as exc:
        return {
            "success": False,
            "message": str(exc),
            "created_pending": 0,
            "uploaded": 0,
            "failed": 0,
            "skipped": 0,
            "status": attendance_sync_status_summary(),
        }
    finally:
        ATTENDANCE_SYNC_LOCK.release()
