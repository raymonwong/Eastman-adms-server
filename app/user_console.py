from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.database import SessionLocal
from sqlalchemy import or_

from app.models import Device, DeviceUser, DeviceUserFingerprint, DeviceUserSync

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

DEVICE_ROLE_MAP = {
    "NORMAL": {"privilege": "0", "label": "Normal User / 普通用户"},
    "ADMIN": {"privilege": "14", "label": "Administrator / 管理员"},
}


class AdmsUserResponse(BaseModel):
    id: int
    employee_id: str | None
    employee_record_id: str | None
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
    fingerprint_count: int
    sync_details: list[dict[str, object | None]]


class DeviceOptionResponse(BaseModel):
    device_sn: str
    device_name: str | None
    location: str | None
    status: str | None
    label: str


class DeviceRoleRequest(BaseModel):
    role_code: str
    device_sns: list[str]


class DeviceRoleResponse(BaseModel):
    success: bool
    user_id: int
    employee_id: str
    role_code: str
    target_privilege: str
    sync_records: int
    devices: list[str]
    message: str


def _pin_aliases(pin: str | None) -> set[str]:
    value = str(pin or "").strip()
    if not value:
        return set()
    aliases = {value}
    if value.isdigit():
        aliases.add(value.lstrip("0") or "0")
        aliases.add(value.zfill(5))
    return aliases


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
            "target_privilege": record.target_privilege,
            "role_name": record.role_name,
        }
        for record in records
    ]


def _device_label(device: Device) -> str:
    parts = [device.device_name or "Unnamed Device", device.device_sn]
    if device.location:
        parts.append(device.location)
    return " · ".join(parts)


def _fingerprint_count(session, user: DeviceUser) -> int:
    aliases = _pin_aliases(user.pin) | _pin_aliases(user.employee_id)
    if not aliases:
        return 0
    return (
        session.query(DeviceUserFingerprint)
        .filter(DeviceUserFingerprint.pin.in_(aliases))
        .count()
    )


def _user_to_response(session, user: DeviceUser) -> AdmsUserResponse:
    counts = _sync_counts(session, user.employee_id)
    return AdmsUserResponse(
        id=user.id,
        employee_id=user.employee_id,
        employee_record_id=user.employee_record_id,
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
        fingerprint_count=_fingerprint_count(session, user),
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


@router.get("/api/adms-users/devices", response_model=list[DeviceOptionResponse])
def api_list_role_devices() -> list[DeviceOptionResponse]:
    with SessionLocal() as session:
        devices = (
            session.query(Device)
            .filter(Device.record_attendance.is_(True))
            .order_by(Device.updated_at.desc(), Device.device_sn.asc())
            .all()
        )
        return [
            DeviceOptionResponse(
                device_sn=device.device_sn,
                device_name=device.device_name,
                location=device.location,
                status=device.status,
                label=_device_label(device),
            )
            for device in devices
        ]


@router.post("/api/adms-users/{user_id}/role", response_model=DeviceRoleResponse)
def api_set_device_role(user_id: int, payload: DeviceRoleRequest) -> DeviceRoleResponse:
    role_code = (payload.role_code or "").strip().upper()
    if role_code not in DEVICE_ROLE_MAP:
        raise HTTPException(status_code=422, detail="Unsupported role_code. Use NORMAL or ADMIN.")

    device_sns = sorted({str(device_sn or "").strip() for device_sn in payload.device_sns if str(device_sn or "").strip()})
    if not device_sns:
        raise HTTPException(status_code=422, detail="At least one device_sn is required.")

    role = DEVICE_ROLE_MAP[role_code]
    target_privilege = role["privilege"]

    with SessionLocal() as session:
        user = session.get(DeviceUser, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="ADMS user not found.")
        if not user.employee_id:
            raise HTTPException(status_code=422, detail="Only Mingdao users with employee_id can be synchronized to devices.")
        if not user.pin:
            raise HTTPException(status_code=422, detail="User has no device PIN.")

        devices = (
            session.query(Device)
            .filter(Device.device_sn.in_(device_sns))
            .filter(Device.record_attendance.is_(True))
            .order_by(Device.device_sn.asc())
            .all()
        )
        valid_device_sns = [device.device_sn for device in devices]
        if not valid_device_sns:
            raise HTTPException(status_code=422, detail="No enabled attendance devices were selected.")

        sync_records = 0
        for device_sn in valid_device_sns:
            sync_record = (
                session.query(DeviceUserSync)
                .filter(DeviceUserSync.employee_id == user.employee_id, DeviceUserSync.device_sn == device_sn)
                .one_or_none()
            )
            if sync_record is None:
                sync_record = DeviceUserSync(employee_id=user.employee_id, device_sn=device_sn)
                session.add(sync_record)

            sync_record.target_privilege = target_privilege
            sync_record.role_name = role_code
            sync_record.sync_status = "PENDING"
            sync_record.retry_count = 0
            sync_record.last_error = None
            sync_records += 1

        session.commit()

    return DeviceRoleResponse(
        success=True,
        user_id=user_id,
        employee_id=user.employee_id,
        role_code=role_code,
        target_privilege=target_privilege,
        sync_records=sync_records,
        devices=valid_device_sns,
        message=f"{role['label']} queued for {sync_records} device(s).",
    )
