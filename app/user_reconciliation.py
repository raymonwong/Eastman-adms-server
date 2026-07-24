from datetime import datetime, timedelta
import os
from zoneinfo import ZoneInfo

from app.database import SessionLocal
from app.integration_config import get_config_values, save_config_values
from app.models import Device, DeviceUser, DeviceUserFingerprint, DeviceUserFingerprintSync, DeviceUserSync

USER_RECONCILIATION_CONFIG_KEYS = {
    "enabled": "USER_RECONCILIATION_ENABLED",
    "frequency": "USER_RECONCILIATION_FREQUENCY",
    "weekday": "USER_RECONCILIATION_WEEKDAY",
    "time": "USER_RECONCILIATION_TIME",
    "timezone": "USER_RECONCILIATION_TIMEZONE",
    "last_run_at": "USER_RECONCILIATION_LAST_RUN_AT",
    "last_result": "USER_RECONCILIATION_LAST_RESULT",
    "last_sync_records": "USER_RECONCILIATION_LAST_SYNC_RECORDS",
}

DEFAULT_USER_RECONCILIATION_CONFIG = {
    USER_RECONCILIATION_CONFIG_KEYS["enabled"]: "true",
    USER_RECONCILIATION_CONFIG_KEYS["frequency"]: "daily",
    USER_RECONCILIATION_CONFIG_KEYS["weekday"]: "0",
    USER_RECONCILIATION_CONFIG_KEYS["time"]: "03:00",
    USER_RECONCILIATION_CONFIG_KEYS["timezone"]: "Asia/Dubai",
    USER_RECONCILIATION_CONFIG_KEYS["last_run_at"]: "",
    USER_RECONCILIATION_CONFIG_KEYS["last_result"]: "Not run",
    USER_RECONCILIATION_CONFIG_KEYS["last_sync_records"]: "0",
}

_LAST_SCHEDULE_KEY: str | None = None


def _settings() -> dict[str, str]:
    values = DEFAULT_USER_RECONCILIATION_CONFIG.copy()
    values.update(get_config_values(list(USER_RECONCILIATION_CONFIG_KEYS.values())))
    for key, default in DEFAULT_USER_RECONCILIATION_CONFIG.items():
        if values.get(key, "") == "":
            values[key] = default
    return values


def _timezone() -> ZoneInfo:
    value = _settings()[USER_RECONCILIATION_CONFIG_KEYS["timezone"]]
    try:
        return ZoneInfo(value)
    except Exception:
        return ZoneInfo("Asia/Dubai")


def _parse_time(value: str) -> tuple[int, int]:
    hour_text, minute_text = value.split(":", 1)
    return int(hour_text), int(minute_text)


def _next_run_at(now: datetime | None = None) -> datetime:
    settings = _settings()
    tz = _timezone()
    current = now.astimezone(tz) if now else datetime.now(tz)
    hour, minute = _parse_time(settings[USER_RECONCILIATION_CONFIG_KEYS["time"]])
    frequency = settings[USER_RECONCILIATION_CONFIG_KEYS["frequency"]].lower()
    weekday = int(settings[USER_RECONCILIATION_CONFIG_KEYS["weekday"]] or "0")

    candidate = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if frequency == "weekly":
        days_ahead = (weekday - current.weekday()) % 7
        candidate = candidate + timedelta(days=days_ahead)
        if candidate <= current:
            candidate = candidate + timedelta(days=7)
        return candidate

    if candidate <= current:
        candidate = candidate + timedelta(days=1)
    return candidate


def user_reconciliation_config() -> dict[str, object]:
    values = _settings()
    enabled = values[USER_RECONCILIATION_CONFIG_KEYS["enabled"]].lower() == "true"
    frequency = values[USER_RECONCILIATION_CONFIG_KEYS["frequency"]].lower()
    weekday = int(values[USER_RECONCILIATION_CONFIG_KEYS["weekday"]] or "0")
    time_value = values[USER_RECONCILIATION_CONFIG_KEYS["time"]]
    timezone_value = values[USER_RECONCILIATION_CONFIG_KEYS["timezone"]]
    return {
        "enabled": enabled,
        "frequency": frequency,
        "weekday": weekday,
        "time": time_value,
        "timezone": timezone_value,
        "next_run_at": _next_run_at().isoformat(timespec="seconds") if enabled else "",
        "last_run_at": values[USER_RECONCILIATION_CONFIG_KEYS["last_run_at"]],
        "last_result": values[USER_RECONCILIATION_CONFIG_KEYS["last_result"]],
        "last_sync_records": int(values[USER_RECONCILIATION_CONFIG_KEYS["last_sync_records"]] or "0"),
    }


def save_user_reconciliation_config(*, enabled: bool, frequency: str, weekday: int, time_value: str) -> dict[str, object]:
    values = {
        USER_RECONCILIATION_CONFIG_KEYS["enabled"]: "true" if enabled else "false",
        USER_RECONCILIATION_CONFIG_KEYS["frequency"]: frequency,
        USER_RECONCILIATION_CONFIG_KEYS["weekday"]: str(weekday),
        USER_RECONCILIATION_CONFIG_KEYS["time"]: time_value,
        USER_RECONCILIATION_CONFIG_KEYS["timezone"]: "Asia/Dubai",
    }
    os.environ.update(values)
    save_config_values(values)
    return user_reconciliation_config()


def run_user_reconciliation() -> dict[str, object]:
    sync_records = 0
    fingerprint_sync_records = 0
    with SessionLocal() as session:
        devices = (
            session.query(Device)
            .filter(Device.record_attendance.is_(True))
            .order_by(Device.device_sn.asc())
            .all()
        )
        users = (
            session.query(DeviceUser)
            .filter(DeviceUser.employee_id.is_not(None), DeviceUser.employee_id != "")
            .filter(DeviceUser.pin.is_not(None), DeviceUser.pin != "")
            .order_by(DeviceUser.employee_id.asc())
            .all()
        )

        active_device_sns = {device.device_sn for device in devices}
        if active_device_sns:
            (
                session.query(DeviceUserSync)
                .filter(DeviceUserSync.device_sn.not_in(active_device_sns))
                .delete(synchronize_session=False)
            )
            (
                session.query(DeviceUserFingerprintSync)
                .filter(DeviceUserFingerprintSync.device_sn.not_in(active_device_sns))
                .delete(synchronize_session=False)
            )

        fingerprints = (
            session.query(DeviceUserFingerprint)
            .order_by(DeviceUserFingerprint.pin.asc(), DeviceUserFingerprint.finger_id.asc())
            .all()
        )

        for device in devices:
            for user in users:
                sync_record = (
                    session.query(DeviceUserSync)
                    .filter(DeviceUserSync.employee_id == user.employee_id, DeviceUserSync.device_sn == device.device_sn)
                    .one_or_none()
                )
                if sync_record is None:
                    sync_record = DeviceUserSync(employee_id=user.employee_id, device_sn=device.device_sn)
                    session.add(sync_record)

                sync_record.sync_status = "PENDING"
                sync_record.retry_count = 0
                sync_record.last_error = None
                sync_records += 1

            for fingerprint in fingerprints:
                fingerprint_sync = (
                    session.query(DeviceUserFingerprintSync)
                    .filter(
                        DeviceUserFingerprintSync.pin == fingerprint.pin,
                        DeviceUserFingerprintSync.finger_id == fingerprint.finger_id,
                        DeviceUserFingerprintSync.device_sn == device.device_sn,
                    )
                    .one_or_none()
                )
                if fingerprint_sync is None:
                    fingerprint_sync = DeviceUserFingerprintSync(
                        fingerprint_id=fingerprint.id,
                        device_sn=device.device_sn,
                        pin=fingerprint.pin,
                        finger_id=fingerprint.finger_id,
                        template_hash=fingerprint.template_hash,
                    )
                    session.add(fingerprint_sync)
                else:
                    fingerprint_sync.fingerprint_id = fingerprint.id
                    fingerprint_sync.template_hash = fingerprint.template_hash
                # A device can delete fingerprints locally without notifying ADMS.
                # The reconciliation schedule therefore re-queues every stored
                # fingerprint, so each attendance device can restore missing FP data.
                fingerprint_sync.sync_status = "PENDING"
                fingerprint_sync.retry_count = 0
                fingerprint_sync.last_error = None
                fingerprint_sync.last_sync_time = None
                fingerprint_sync_records += 1

        session.commit()

    now_text = datetime.now(_timezone()).isoformat(timespec="seconds")
    total_sync_records = sync_records + fingerprint_sync_records
    result_text = f"Queued {sync_records} user sync records and {fingerprint_sync_records} fingerprint sync records"
    save_config_values(
        {
            USER_RECONCILIATION_CONFIG_KEYS["last_run_at"]: now_text,
            USER_RECONCILIATION_CONFIG_KEYS["last_result"]: result_text,
            USER_RECONCILIATION_CONFIG_KEYS["last_sync_records"]: str(total_sync_records),
        }
    )
    return {
        "success": True,
        "sync_records": total_sync_records,
        "user_sync_records": sync_records,
        "fingerprint_sync_records": fingerprint_sync_records,
        "last_run_at": now_text,
        "message": result_text,
    }


def run_due_user_reconciliation() -> dict[str, object] | None:
    global _LAST_SCHEDULE_KEY

    settings = _settings()
    if settings[USER_RECONCILIATION_CONFIG_KEYS["enabled"]].lower() != "true":
        return None

    tz = _timezone()
    now = datetime.now(tz)
    hour, minute = _parse_time(settings[USER_RECONCILIATION_CONFIG_KEYS["time"]])
    if now.hour != hour or now.minute != minute:
        return None

    frequency = settings[USER_RECONCILIATION_CONFIG_KEYS["frequency"]].lower()
    weekday = int(settings[USER_RECONCILIATION_CONFIG_KEYS["weekday"]] or "0")
    if frequency == "weekly" and now.weekday() != weekday:
        return None

    schedule_key = f"{frequency}:{now.date().isoformat()}:{hour:02d}:{minute:02d}"
    if _LAST_SCHEDULE_KEY == schedule_key:
        return None

    _LAST_SCHEDULE_KEY = schedule_key
    return run_user_reconciliation()


def user_reconciliation_check_interval_seconds() -> int:
    return 60
