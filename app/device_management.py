from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.database import SessionLocal
from app.models import Device, DeviceUser, DeviceUserFingerprint, DeviceUserFingerprintSync, DeviceUserSync

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


class DeviceResponse(BaseModel):
    id: int
    device_sn: str
    device_name: str | None
    location: str | None
    record_attendance: bool
    show_in_console: bool
    created_at: datetime
    updated_at: datetime


class DeviceUpdateRequest(BaseModel):
    device_name: str = Field(min_length=1, max_length=128)
    location: str | None = Field(default=None, max_length=255)
    record_attendance: bool
    show_in_console: bool


def _device_to_response(device: Device) -> DeviceResponse:
    return DeviceResponse(
        id=device.id,
        device_sn=device.device_sn,
        device_name=device.device_name,
        location=device.location,
        record_attendance=bool(device.record_attendance),
        show_in_console=bool(device.show_in_console),
        created_at=device.created_at,
        updated_at=device.updated_at,
    )


def _list_devices() -> list[DeviceResponse]:
    with SessionLocal() as session:
        devices = session.query(Device).order_by(Device.updated_at.desc(), Device.device_sn.asc()).all()
        return [_device_to_response(device) for device in devices]


def _get_device(sn: str) -> DeviceResponse:
    with SessionLocal() as session:
        device = session.query(Device).filter(Device.device_sn == sn).one_or_none()
        if device is None:
            raise HTTPException(status_code=404, detail="Device not found")
        return _device_to_response(device)


def _rebuild_device_user_sync_records(session, device_sn: str) -> int:
    sync_count = 0
    users = (
        session.query(DeviceUser)
        .filter(DeviceUser.employee_id.is_not(None), DeviceUser.employee_id != "")
        .order_by(DeviceUser.employee_id.asc())
        .all()
    )

    for user in users:
        sync_record = (
            session.query(DeviceUserSync)
            .filter(DeviceUserSync.employee_id == user.employee_id, DeviceUserSync.device_sn == device_sn)
            .one_or_none()
        )
        if sync_record is None:
            sync_record = DeviceUserSync(employee_id=user.employee_id, device_sn=device_sn)
            session.add(sync_record)
        sync_record.sync_status = "PENDING"
        sync_record.retry_count = 0
        sync_record.last_error = None
        sync_count += 1
    return sync_count


def _rebuild_device_fingerprint_sync_records(session, device_sn: str) -> int:
    sync_count = 0
    fingerprints = (
        session.query(DeviceUserFingerprint)
        .order_by(DeviceUserFingerprint.pin.asc(), DeviceUserFingerprint.finger_id.asc())
        .all()
    )

    for fingerprint in fingerprints:
        sync_record = (
            session.query(DeviceUserFingerprintSync)
            .filter(
                DeviceUserFingerprintSync.pin == fingerprint.pin,
                DeviceUserFingerprintSync.finger_id == fingerprint.finger_id,
                DeviceUserFingerprintSync.device_sn == device_sn,
            )
            .one_or_none()
        )
        if sync_record is None:
            sync_record = DeviceUserFingerprintSync(
                fingerprint_id=fingerprint.id,
                device_sn=device_sn,
                pin=fingerprint.pin,
                finger_id=fingerprint.finger_id,
                template_hash=fingerprint.template_hash,
            )
            session.add(sync_record)
        elif sync_record.template_hash != fingerprint.template_hash or sync_record.sync_status != "SYNCED":
            sync_record.fingerprint_id = fingerprint.id
            sync_record.template_hash = fingerprint.template_hash
            sync_record.sync_status = "PENDING"
            sync_record.retry_count = 0
            sync_record.last_error = None
            sync_record.last_sync_time = None
        else:
            continue
        sync_count += 1

    return sync_count


def _update_device(sn: str, payload: DeviceUpdateRequest) -> DeviceResponse:
    with SessionLocal() as session:
        device = session.query(Device).filter(Device.device_sn == sn).one_or_none()
        if device is None:
            raise HTTPException(status_code=404, detail="Device not found")

        previous_record_attendance = bool(device.record_attendance)
        device.device_name = payload.device_name.strip()
        device.location = payload.location.strip() if payload.location else None
        device.record_attendance = payload.record_attendance
        device.show_in_console = payload.show_in_console

        if previous_record_attendance and not payload.record_attendance:
            (
                session.query(DeviceUserSync)
                .filter(DeviceUserSync.device_sn == device.device_sn)
                .delete(synchronize_session=False)
            )
            (
                session.query(DeviceUserFingerprintSync)
                .filter(DeviceUserFingerprintSync.device_sn == device.device_sn)
                .delete(synchronize_session=False)
            )
        elif not previous_record_attendance and payload.record_attendance:
            _rebuild_device_user_sync_records(session, device.device_sn)
            _rebuild_device_fingerprint_sync_records(session, device.device_sn)

        session.commit()
        session.refresh(device)
        return _device_to_response(device)


@router.get("/dms", response_class=HTMLResponse)
async def device_management_page(request: Request):
    return templates.TemplateResponse("devices.html", {"request": request})


@router.get("/api/devices", response_model=list[DeviceResponse])
def api_list_devices() -> list[DeviceResponse]:
    return _list_devices()


@router.get("/api/device/{sn}", response_model=DeviceResponse)
def api_get_device(sn: str) -> DeviceResponse:
    return _get_device(sn)


@router.put("/api/device/{sn}", response_model=DeviceResponse)
def api_update_device(sn: str, payload: DeviceUpdateRequest) -> DeviceResponse:
    return _update_device(sn, payload)
