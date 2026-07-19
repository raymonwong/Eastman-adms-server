import json
import os
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func

from app.backup_settings import _payload as backup_payload
from app.console import _classify_device
from app.database import SessionLocal
from app.integration_config import get_config_value, get_config_values, save_config_values
from app.models import AttendanceMingdaoSync, Device, DeviceUserFingerprintSync, DeviceUserSync, RawRequest

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

DUBAI_TZ = ZoneInfo("Asia/Dubai")

ALERT_CONFIG_KEYS = {
    "enabled": "ADMS_ALERT_ENABLED",
    "webhook_url": "ADMS_ALERT_WEBHOOK_URL",
    "check_interval_seconds": "ADMS_ALERT_CHECK_INTERVAL_SECONDS",
    "cooldown_minutes": "ADMS_ALERT_COOLDOWN_MINUTES",
    "device_offline_minutes": "ADMS_ALERT_DEVICE_OFFLINE_MINUTES",
    "heartbeat_timeout_minutes": "ADMS_ALERT_HEARTBEAT_TIMEOUT_MINUTES",
    "attendance_failed_threshold": "ADMS_ALERT_ATTENDANCE_FAILED_THRESHOLD",
    "user_failed_threshold": "ADMS_ALERT_USER_FAILED_THRESHOLD",
    "fingerprint_failed_threshold": "ADMS_ALERT_FINGERPRINT_FAILED_THRESHOLD",
    "backup_max_age_hours": "ADMS_ALERT_BACKUP_MAX_AGE_HOURS",
}

DEFAULT_ALERT_CONFIG = {
    ALERT_CONFIG_KEYS["enabled"]: "true",
    ALERT_CONFIG_KEYS["webhook_url"]: "",
    ALERT_CONFIG_KEYS["check_interval_seconds"]: "60",
    ALERT_CONFIG_KEYS["cooldown_minutes"]: "30",
    ALERT_CONFIG_KEYS["device_offline_minutes"]: "5",
    ALERT_CONFIG_KEYS["heartbeat_timeout_minutes"]: "5",
    ALERT_CONFIG_KEYS["attendance_failed_threshold"]: "1",
    ALERT_CONFIG_KEYS["user_failed_threshold"]: "1",
    ALERT_CONFIG_KEYS["fingerprint_failed_threshold"]: "1",
    ALERT_CONFIG_KEYS["backup_max_age_hours"]: "36",
}


class AlertConfigRequest(BaseModel):
    enabled: bool = True
    webhook_url: str = Field(default="", max_length=1000)
    check_interval_seconds: int = Field(ge=30, le=3600)
    cooldown_minutes: int = Field(ge=1, le=1440)
    device_offline_minutes: int = Field(ge=1, le=1440)
    heartbeat_timeout_minutes: int = Field(ge=1, le=1440)
    attendance_failed_threshold: int = Field(ge=1, le=100000)
    user_failed_threshold: int = Field(ge=1, le=100000)
    fingerprint_failed_threshold: int = Field(ge=1, le=100000)
    backup_max_age_hours: int = Field(ge=1, le=8760)

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned and not cleaned.startswith(("http://", "https://")):
            raise ValueError("Webhook URL must start with http:// or https://.")
        return cleaned


def _int_value(values: dict[str, str], key: str, default: int) -> int:
    try:
        return int((values.get(key) or str(default)).strip())
    except ValueError:
        return default


def alert_config() -> dict[str, object]:
    values = DEFAULT_ALERT_CONFIG | get_config_values(list(ALERT_CONFIG_KEYS.values()))
    return {
        "enabled": (values.get(ALERT_CONFIG_KEYS["enabled"]) or "true").strip().lower() == "true",
        "webhook_url": (values.get(ALERT_CONFIG_KEYS["webhook_url"]) or "").strip(),
        "check_interval_seconds": _int_value(values, ALERT_CONFIG_KEYS["check_interval_seconds"], 60),
        "cooldown_minutes": _int_value(values, ALERT_CONFIG_KEYS["cooldown_minutes"], 30),
        "device_offline_minutes": _int_value(values, ALERT_CONFIG_KEYS["device_offline_minutes"], 5),
        "heartbeat_timeout_minutes": _int_value(values, ALERT_CONFIG_KEYS["heartbeat_timeout_minutes"], 5),
        "attendance_failed_threshold": _int_value(values, ALERT_CONFIG_KEYS["attendance_failed_threshold"], 1),
        "user_failed_threshold": _int_value(values, ALERT_CONFIG_KEYS["user_failed_threshold"], 1),
        "fingerprint_failed_threshold": _int_value(values, ALERT_CONFIG_KEYS["fingerprint_failed_threshold"], 1),
        "backup_max_age_hours": _int_value(values, ALERT_CONFIG_KEYS["backup_max_age_hours"], 36),
    }


def alert_check_interval_seconds() -> int:
    return int(alert_config()["check_interval_seconds"])


def _format_dubai(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.replace(tzinfo=UTC).astimezone(DUBAI_TZ).strftime("%Y-%m-%d %H:%M:%S (UTC+4)")


def _latest_heartbeat(session, device_sn: str) -> datetime | None:
    return (
        session.query(func.max(RawRequest.received_at))
        .filter(RawRequest.device_sn == device_sn, RawRequest.request_path == "/iclock/getrequest")
        .scalar()
    )


def evaluate_alerts() -> dict[str, object]:
    config = alert_config()
    now = datetime.now(UTC).replace(tzinfo=None)
    alerts: list[dict[str, object]] = []
    with SessionLocal() as session:
        devices = session.query(Device).filter(Device.show_in_console.is_(True)).all()
        for device in devices:
            last_heartbeat = _latest_heartbeat(session, device.device_sn)
            if last_heartbeat is None:
                age_minutes = None
            else:
                age_minutes = int((now - last_heartbeat).total_seconds() // 60)
            if _classify_device(last_heartbeat) == "OFFLINE" and (
                age_minutes is None or age_minutes >= int(config["device_offline_minutes"])
            ):
                alerts.append(
                    {
                        "code": f"DEVICE_OFFLINE:{device.device_sn}",
                        "type": "DEVICE_OFFLINE",
                        "severity": "critical",
                        "title": "Device Offline / 设备离线",
                        "message": f"{device.device_name or device.device_sn} has no recent communication.",
                        "device_sn": device.device_sn,
                        "device_name": device.device_name or f"New Machine ({device.device_sn})",
                        "last_seen": _format_dubai(last_heartbeat),
                    }
                )
            if age_minutes is not None and age_minutes >= int(config["heartbeat_timeout_minutes"]):
                alerts.append(
                    {
                        "code": f"HEARTBEAT_TIMEOUT:{device.device_sn}",
                        "type": "HEARTBEAT_TIMEOUT",
                        "severity": "warning",
                        "title": "Heartbeat Timeout / 心跳超时",
                        "message": f"{device.device_name or device.device_sn} heartbeat is {age_minutes} minutes old.",
                        "device_sn": device.device_sn,
                        "device_name": device.device_name or f"New Machine ({device.device_sn})",
                        "last_heartbeat": _format_dubai(last_heartbeat),
                    }
                )

        attendance_failed = session.query(func.count(AttendanceMingdaoSync.id)).filter(
            AttendanceMingdaoSync.sync_status == "FAILED"
        ).scalar()
        if attendance_failed >= int(config["attendance_failed_threshold"]):
            alerts.append(
                {
                    "code": "ATTENDANCE_SYNC_FAILED",
                    "type": "ATTENDANCE_SYNC_FAILED",
                    "severity": "critical",
                    "title": "Attendance Sync Failed / 考勤同步失败",
                    "message": f"{attendance_failed} attendance sync records are failed.",
                    "count": attendance_failed,
                }
            )

        user_failed = session.query(func.count(DeviceUserSync.id)).filter(DeviceUserSync.sync_status == "FAILED").scalar()
        if user_failed >= int(config["user_failed_threshold"]):
            alerts.append(
                {
                    "code": "USER_SYNC_FAILED",
                    "type": "USER_SYNC_FAILED",
                    "severity": "warning",
                    "title": "User Sync Failed / 用户同步失败",
                    "message": f"{user_failed} user sync records are failed.",
                    "count": user_failed,
                }
            )

        fingerprint_failed = session.query(func.count(DeviceUserFingerprintSync.id)).filter(
            DeviceUserFingerprintSync.sync_status == "FAILED"
        ).scalar()
        if fingerprint_failed >= int(config["fingerprint_failed_threshold"]):
            alerts.append(
                {
                    "code": "FINGERPRINT_SYNC_FAILED",
                    "type": "FINGERPRINT_SYNC_FAILED",
                    "severity": "warning",
                    "title": "Fingerprint Sync Failed / 指纹同步失败",
                    "message": f"{fingerprint_failed} fingerprint sync records are failed.",
                    "count": fingerprint_failed,
                }
            )

    backup_data = backup_payload()
    latest_backup = backup_data.get("latest_backup")
    if not latest_backup:
        alerts.append(
            {
                "code": "BACKUP_MISSING",
                "type": "BACKUP_MISSING",
                "severity": "critical",
                "title": "Backup Missing / 缺少备份",
                "message": "No backup package has been created yet.",
            }
        )
    else:
        created_text = str(latest_backup.get("created_at", "")).replace(" (UTC+4)", "")
        try:
            created_at_dubai = datetime.strptime(created_text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=DUBAI_TZ)
            age_hours = int((datetime.now(DUBAI_TZ) - created_at_dubai).total_seconds() // 3600)
            if age_hours >= int(config["backup_max_age_hours"]):
                alerts.append(
                    {
                        "code": "BACKUP_STALE",
                        "type": "BACKUP_STALE",
                        "severity": "warning",
                        "title": "Backup Stale / 备份过期",
                        "message": f"Latest backup is {age_hours} hours old.",
                        "latest_backup": latest_backup.get("filename"),
                        "latest_backup_time": latest_backup.get("created_at"),
                    }
                )
        except ValueError:
            pass

    return {
        "enabled": config["enabled"],
        "webhook_configured": bool(config["webhook_url"]),
        "server_time": datetime.now(DUBAI_TZ).strftime("%Y-%m-%d %H:%M:%S (UTC+4)"),
        "alert_count": len(alerts),
        "critical_count": sum(1 for alert in alerts if alert["severity"] == "critical"),
        "warning_count": sum(1 for alert in alerts if alert["severity"] == "warning"),
        "alerts": alerts,
        "config": config,
    }


def _last_sent_key(code: str) -> str:
    safe_code = "".join(ch if ch.isalnum() else "_" for ch in code.upper())
    return f"ADMS_ALERT_LAST_SENT_{safe_code}"


def _should_send(code: str, cooldown_minutes: int) -> bool:
    last_sent = get_config_value(_last_sent_key(code), "")
    if not last_sent:
        return True
    try:
        last_dt = datetime.fromisoformat(last_sent)
    except ValueError:
        return True
    return datetime.now(UTC) - last_dt >= timedelta(minutes=cooldown_minutes)


def _send_webhook(webhook_url: str, payload: dict[str, object]) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        response.read()


def process_alert_notifications() -> dict[str, object]:
    data = evaluate_alerts()
    config = alert_config()
    if not data["enabled"] or not config["webhook_url"]:
        return data | {"sent_count": 0, "send_errors": []}
    sent_count = 0
    send_errors: list[str] = []
    for alert in data["alerts"]:
        code = str(alert["code"])
        if not _should_send(code, int(config["cooldown_minutes"])):
            continue
        try:
            _send_webhook(str(config["webhook_url"]), {"project": "eastman-adms-server", "alert": alert})
            save_config_values({_last_sent_key(code): datetime.now(UTC).isoformat()})
            sent_count += 1
        except Exception as exc:
            send_errors.append(f"{code}: {exc}")
    return data | {"sent_count": sent_count, "send_errors": send_errors}


@router.get("/settings/alerts", response_class=HTMLResponse)
def alerts_page(request: Request):
    return templates.TemplateResponse("alerts.html", {"request": request, "data": evaluate_alerts()})


@router.get("/api/settings/alerts")
def alerts_data() -> JSONResponse:
    return JSONResponse(evaluate_alerts())


@router.post("/api/settings/alerts")
def save_alert_config(payload: AlertConfigRequest) -> dict[str, object]:
    values = {
        ALERT_CONFIG_KEYS["enabled"]: "true" if payload.enabled else "false",
        ALERT_CONFIG_KEYS["webhook_url"]: payload.webhook_url,
        ALERT_CONFIG_KEYS["check_interval_seconds"]: str(payload.check_interval_seconds),
        ALERT_CONFIG_KEYS["cooldown_minutes"]: str(payload.cooldown_minutes),
        ALERT_CONFIG_KEYS["device_offline_minutes"]: str(payload.device_offline_minutes),
        ALERT_CONFIG_KEYS["heartbeat_timeout_minutes"]: str(payload.heartbeat_timeout_minutes),
        ALERT_CONFIG_KEYS["attendance_failed_threshold"]: str(payload.attendance_failed_threshold),
        ALERT_CONFIG_KEYS["user_failed_threshold"]: str(payload.user_failed_threshold),
        ALERT_CONFIG_KEYS["fingerprint_failed_threshold"]: str(payload.fingerprint_failed_threshold),
        ALERT_CONFIG_KEYS["backup_max_age_hours"]: str(payload.backup_max_age_hours),
    }
    os.environ.update(values)
    save_config_values(values)
    return {"saved": True, "message": "Alert settings saved. / 告警设置已保存。", "data": evaluate_alerts()}


@router.post("/api/settings/alerts/test")
def test_alert_webhook() -> dict[str, object]:
    config = alert_config()
    if not config["webhook_url"]:
        return {"success": False, "message": "Webhook URL is empty. / Webhook 地址为空。"}
    payload = {
        "project": "eastman-adms-server",
        "alert": {
            "code": "TEST_ALERT",
            "type": "TEST",
            "severity": "info",
            "title": "ADMS Test Alert / ADMS 测试告警",
            "message": "This is a test alert from ADMS Alert Settings.",
        },
    }
    try:
        _send_webhook(str(config["webhook_url"]), payload)
    except Exception as exc:
        return {"success": False, "message": str(exc)}
    return {"success": True, "message": "Test alert sent. / 测试告警已发送。"}
