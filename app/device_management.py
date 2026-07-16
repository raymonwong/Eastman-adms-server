from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.database import SessionLocal
from app.models import Device

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


def _update_device(sn: str, payload: DeviceUpdateRequest) -> DeviceResponse:
    with SessionLocal() as session:
        device = session.query(Device).filter(Device.device_sn == sn).one_or_none()
        if device is None:
            raise HTTPException(status_code=404, detail="Device not found")

        device.device_name = payload.device_name.strip()
        device.location = payload.location.strip() if payload.location else None
        device.record_attendance = payload.record_attendance
        device.show_in_console = payload.show_in_console
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
