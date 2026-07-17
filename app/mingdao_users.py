from datetime import datetime
import os
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field, ValidationError, field_validator
from app.adms import _debug_log
from app.console import _classify_device, _latest_heartbeat
from app.database import SessionLocal
from app.models import Device, DeviceUser, DeviceUserSync

ALLOWED_SYNC_STATUSES = {"PENDING", "SYNCING", "SYNCED", "FAILED"}
SUPPORTED_PRIVILEGES = {0, 1, 2, 3, 6, 10, 14}
SYNC_PENDING = "PENDING"
MAX_BATCH_USERS = 500
DEFAULT_TOKEN_VALUES = {"", "changeme", "changeme-mingdao-token", "password", "123456", "please_change_me"}
MINGDAO_API_RUNTIME_STATE: dict[str, str | None] = {"last_request_time": None, "last_caller_ip": None}


def get_mingdao_api_runtime_state() -> dict[str, str | None]:
    return MINGDAO_API_RUNTIME_STATE.copy()


def require_mingdao_api_token(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    MINGDAO_API_RUNTIME_STATE["last_request_time"] = datetime.now().isoformat(timespec="seconds")
    MINGDAO_API_RUNTIME_STATE["last_caller_ip"] = request.client.host if request.client else None

    expected_token = os.getenv("MINGDAO_API_TOKEN", "").strip()
    if expected_token.lower() in DEFAULT_TOKEN_VALUES:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mingdao API token is not configured.",
        )

    bearer_token = ""
    if authorization:
        parts = authorization.strip().split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            bearer_token = parts[1].strip()

    if x_api_key == expected_token or bearer_token == expected_token:
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid Mingdao API token.",
    )


router = APIRouter(prefix="/api/v1", tags=["Mingdao Users"], dependencies=[Depends(require_mingdao_api_token)])


class UserSyncRequest(BaseModel):
    employee_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    card_no: str | None = Field(default=None, max_length=64)
    privilege: int = Field(default=0, ge=0)
    enabled: bool = True

    @field_validator("employee_id", "name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be empty")
        return cleaned

    @field_validator("department", "card_no")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return _clean_text(value)

    @field_validator("privilege")
    @classmethod
    def validate_privilege(cls, value: int) -> int:
        if value not in SUPPORTED_PRIVILEGES:
            raise ValueError(f"unsupported privilege: {value}")
        return value


class UserSyncResponse(BaseModel):
    success: bool
    employee_id: str
    message: str
    changed: bool = False
    sync_records: int = 0


class UserBatchSyncResponse(BaseModel):
    success: bool
    total: int
    succeeded: int
    failed: int
    results: list[dict[str, object]]


class UserResponse(BaseModel):
    employee_id: str
    name: str
    department: str | None
    card_no: str | None
    privilege: int
    enabled: bool
    created_at: datetime
    updated_at: datetime


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _set_sync_status(sync_record: DeviceUserSync, sync_status: str) -> None:
    normalized_status = sync_status.upper()
    if normalized_status not in ALLOWED_SYNC_STATUSES:
        raise ValueError(f"Unsupported device_user_sync status: {sync_status}")
    sync_record.sync_status = normalized_status


def _privilege_to_int(value: str | None) -> int:
    try:
        return int(value or 0)
    except ValueError:
        return 0


def _user_to_response(user: DeviceUser) -> UserResponse:
    if not user.employee_id:
        raise ValueError("DeviceUser is missing employee_id")
    return UserResponse(
        employee_id=user.employee_id,
        name=user.name or "",
        department=user.department,
        card_no=user.card_no,
        privilege=_privilege_to_int(user.privilege),
        enabled=bool(user.enabled),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _has_user_changed(user: DeviceUser, payload: UserSyncRequest) -> bool:
    return any(
        (
            user.name != payload.name.strip(),
            user.department != _clean_text(payload.department),
            user.card_no != _clean_text(payload.card_no),
            user.card != _clean_text(payload.card_no),
            user.privilege != str(payload.privilege),
            bool(user.enabled) != payload.enabled,
            user.pin != payload.employee_id.strip(),
        )
    )


def _apply_user_payload(user: DeviceUser, payload: UserSyncRequest) -> None:
    employee_id = payload.employee_id.strip()
    card_no = _clean_text(payload.card_no)
    user.employee_id = employee_id
    user.pin = employee_id
    user.name = payload.name.strip()
    user.department = _clean_text(payload.department)
    user.card_no = card_no
    # Keep card aligned for compatibility with existing USER parser fields.
    user.card = card_no
    user.privilege = str(payload.privilege)
    user.enabled = payload.enabled


def _prepare_device_sync_records(session, employee_id: str) -> int:
    sync_count = 0
    devices = session.query(Device).order_by(Device.device_sn.asc()).all()

    for device in devices:
        sync_record = (
            session.query(DeviceUserSync)
            .filter(DeviceUserSync.employee_id == employee_id, DeviceUserSync.device_sn == device.device_sn)
            .one_or_none()
        )
        if sync_record is None:
            sync_record = DeviceUserSync(employee_id=employee_id, device_sn=device.device_sn)
            session.add(sync_record)

        _set_sync_status(sync_record, SYNC_PENDING)
        sync_record.last_error = None
        sync_record.retry_count = 0
        sync_count += 1

        device_status = _classify_device(_latest_heartbeat(session, device.device_sn))
        _debug_log(
            "USER SYNC PENDING",
            {
                "Employee ID": employee_id,
                "Device": device.device_sn,
                "Device Status": device_status,
                "Sync Status": SYNC_PENDING,
            },
        )

    return sync_count


def _upsert_user(payload: UserSyncRequest) -> UserSyncResponse:
    employee_id = payload.employee_id.strip()

    with SessionLocal() as session:
        user = session.query(DeviceUser).filter(DeviceUser.employee_id == employee_id).one_or_none()
        if user is None:
            user = DeviceUser(employee_id=employee_id)
            session.add(user)
            changed = True
        else:
            changed = _has_user_changed(user, payload)

        if not changed:
            session.commit()
            _debug_log(
                "USER UPSERT",
                {
                    "Employee ID": employee_id,
                    "Name": payload.name,
                    "Changed": "False",
                },
            )
            return UserSyncResponse(
                success=True,
                employee_id=employee_id,
                message="User already up to date.",
                changed=False,
                sync_records=0,
            )

        _apply_user_payload(user, payload)
        sync_records = _prepare_device_sync_records(session, employee_id)
        session.commit()

    _debug_log(
        "USER API",
        {
            "Employee ID": employee_id,
            "Name": payload.name,
            "Sync Records": sync_records,
        },
    )
    _debug_log(
        "USER UPSERT",
        {
            "Employee ID": employee_id,
            "Name": payload.name,
            "Changed": "True",
        },
    )

    return UserSyncResponse(
        success=True,
        employee_id=employee_id,
        message="User synchronized successfully.",
        changed=True,
        sync_records=sync_records,
    )


@router.post("/users", response_model=UserSyncResponse)
def sync_user(payload: UserSyncRequest) -> UserSyncResponse:
    return _upsert_user(payload)


@router.post("/users/batch", response_model=UserBatchSyncResponse)
def sync_users_batch(payload: list[dict[str, Any]]) -> UserBatchSyncResponse:
    if len(payload) > MAX_BATCH_USERS:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Batch size exceeds maximum limit of {MAX_BATCH_USERS} users.",
        )

    results: list[dict[str, object]] = []
    succeeded = 0
    failed = 0

    for raw_item in payload:
        employee_id = str(raw_item.get("employee_id", "")).strip()
        try:
            item = UserSyncRequest.model_validate(raw_item)
            result = _upsert_user(item)
            results.append(result.model_dump())
            succeeded += 1
        except (ValidationError, Exception) as exc:
            failed += 1
            _debug_log(
                "USER SYNC FAILED",
                {
                    "Employee ID": employee_id,
                    "Reason": exc,
                },
            )
            results.append(
                {
                    "success": False,
                    "employee_id": employee_id,
                    "message": str(exc),
                }
            )

    return UserBatchSyncResponse(
        success=failed == 0,
        total=len(payload),
        succeeded=succeeded,
        failed=failed,
        results=results,
    )


@router.get("/users", response_model=list[UserResponse])
def list_users() -> list[UserResponse]:
    with SessionLocal() as session:
        users = (
            session.query(DeviceUser)
            .filter(DeviceUser.employee_id.is_not(None), DeviceUser.employee_id != "")
            .order_by(DeviceUser.employee_id.asc())
            .all()
        )
        return [_user_to_response(user) for user in users]


@router.get("/users/{employee_id}", response_model=UserResponse)
def get_user(employee_id: str) -> UserResponse:
    with SessionLocal() as session:
        user = (
            session.query(DeviceUser)
            .filter(DeviceUser.employee_id == employee_id.strip())
            .one_or_none()
        )
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return _user_to_response(user)
