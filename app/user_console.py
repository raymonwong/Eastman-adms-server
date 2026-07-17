from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.database import SessionLocal
from sqlalchemy import or_

from app.models import Device, DeviceUser, DeviceUserSync

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


class AdmsUserResponse(BaseModel):
    id: int
    employee_id: str | None
    pin: str | None
    name: str | None
    department: str | None
    card_no: str | None
    privilege: str | None
    enabled: bool
    last_device_sn: str | None
    last_device_user_upload_at: datetime | None
    created_at: datetime
    updated_at: datetime
    pending_sync: int
    syncing_sync: int
    synced_sync: int
    failed_sync: int
    sync_details: list[dict[str, object | None]]


def _sync_counts(session, employee_id: str | None) -> dict[str, int]:
    if not employee_id:
        return {"PENDING": 0, "SYNCING": 0, "SYNCED": 0, "FAILED": 0}

    rows = (
        session.query(DeviceUserSync.sync_status, DeviceUserSync.id)
        .join(Device, Device.device_sn == DeviceUserSync.device_sn)
        .filter(DeviceUserSync.employee_id == employee_id)
        .filter(Device.record_attendance.is_(True))
        .all()
    )
    counts = {"PENDING": 0, "SYNCING": 0, "SYNCED": 0, "FAILED": 0}
    for status, _ in rows:
        normalized = (status or "").upper()
        if normalized in counts:
            counts[normalized] += 1
    return counts


def _sync_details(session, employee_id: str | None) -> list[dict[str, object | None]]:
    if not employee_id:
        return []

    records = (
        session.query(DeviceUserSync)
        .join(Device, Device.device_sn == DeviceUserSync.device_sn)
        .filter(DeviceUserSync.employee_id == employee_id)
        .filter(Device.record_attendance.is_(True))
        .order_by(DeviceUserSync.device_sn.asc())
        .all()
    )
    return [
        {
            "device_sn": record.device_sn,
            "sync_status": record.sync_status,
            "retry_count": record.retry_count,
            "last_sync_time": record.last_sync_time,
            "last_error": record.last_error,
        }
        for record in records
    ]


def _user_to_response(session, user: DeviceUser) -> AdmsUserResponse:
    counts = _sync_counts(session, user.employee_id)
    return AdmsUserResponse(
        id=user.id,
        employee_id=user.employee_id,
        pin=user.pin,
        name=user.name,
        department=user.department,
        card_no=user.card_no or user.card,
        privilege=user.privilege,
        enabled=bool(user.enabled),
        last_device_sn=user.last_device_sn,
        last_device_user_upload_at=user.last_device_user_upload_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
        pending_sync=counts["PENDING"],
        syncing_sync=counts["SYNCING"],
        synced_sync=counts["SYNCED"],
        failed_sync=counts["FAILED"],
        sync_details=_sync_details(session, user.employee_id),
    )


def _list_adms_users() -> list[AdmsUserResponse]:
    with SessionLocal() as session:
        users = (
            session.query(DeviceUser)
            .filter(
                or_(
                    DeviceUser.employee_id.is_not(None),
                    DeviceUser.pin.is_not(None),
                    DeviceUser.name.is_not(None),
                )
            )
            .order_by(DeviceUser.updated_at.desc(), DeviceUser.employee_id.asc())
            .all()
        )
        return [_user_to_response(session, user) for user in users]


@router.get("/users", response_class=HTMLResponse)
async def adms_users_page(request: Request):
    return templates.TemplateResponse("users.html", {"request": request})


@router.get("/api/adms-users", response_model=list[AdmsUserResponse])
def api_list_adms_users() -> list[AdmsUserResponse]:
    return _list_adms_users()
