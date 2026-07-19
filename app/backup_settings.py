import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator

from app.integration_config import get_config_values, save_config_values

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

DUBAI_TZ = ZoneInfo("Asia/Dubai")
BACKUP_FILE_RE = re.compile(r"^eastman-adms-backup-\d{8}_\d{6}\.tar\.gz$")

BACKUP_CONFIG_KEYS = {
    "enabled": "ADMS_BACKUP_ENABLED",
    "time": "ADMS_BACKUP_TIME",
    "retention_count": "ADMS_BACKUP_RETENTION_COUNT",
    "host_dir": "ADMS_BACKUP_HOST_DIR",
    "container_dir": "ADMS_BACKUP_CONTAINER_DIR",
}

DEFAULT_BACKUP_CONFIG = {
    BACKUP_CONFIG_KEYS["enabled"]: "true",
    BACKUP_CONFIG_KEYS["time"]: "03:30",
    BACKUP_CONFIG_KEYS["retention_count"]: "14",
    BACKUP_CONFIG_KEYS["host_dir"]: "/opt/eastman/Eastman-adms-server/backups",
    BACKUP_CONFIG_KEYS["container_dir"]: "/app/backup",
}


class BackupConfigRequest(BaseModel):
    enabled: bool = True
    time: str = Field(min_length=5, max_length=5)
    retention_count: int = Field(ge=1, le=365)
    host_dir: str = Field(min_length=1, max_length=500)
    container_dir: str = Field(min_length=1, max_length=500)

    @field_validator("time")
    @classmethod
    def validate_time(cls, value: str) -> str:
        if not re.fullmatch(r"\d{2}:\d{2}", value):
            raise ValueError("Backup time must use HH:MM format.")
        hour, minute = (int(part) for part in value.split(":"))
        if hour > 23 or minute > 59:
            raise ValueError("Backup time must be a valid 24-hour time.")
        return value

    @field_validator("host_dir", "container_dir")
    @classmethod
    def validate_absolute_path(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith("/"):
            raise ValueError("Backup directory must be an absolute path.")
        return cleaned


def _env_file_candidates() -> list[Path]:
    candidates: list[Path] = []
    configured = os.getenv("ENV_FILE")
    if configured:
        candidates.append(Path(configured))
    candidates.extend([Path.cwd() / ".env", Path("/app/.env")])
    return candidates


def _save_values_to_env_file(values: dict[str, str]) -> dict[str, object]:
    for path in _env_file_candidates():
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        updated_keys: set[str] = set()
        next_lines: list[str] = []
        for line in lines:
            key = line.split("=", 1)[0] if "=" in line else ""
            if key in values:
                next_lines.append(f"{key}={values[key]}")
                updated_keys.add(key)
            else:
                next_lines.append(line)
        for key, value in values.items():
            if key not in updated_keys:
                next_lines.append(f"{key}={value}")
        path.write_text("\n".join(next_lines) + "\n", encoding="utf-8")
        return {"saved": True, "path": str(path)}
    return {"saved": False, "path": ""}


def _backup_config() -> dict[str, object]:
    values = DEFAULT_BACKUP_CONFIG | get_config_values(list(BACKUP_CONFIG_KEYS.values()))
    retention_text = (values.get(BACKUP_CONFIG_KEYS["retention_count"]) or "14").strip()
    try:
        retention_count = int(retention_text)
    except ValueError:
        retention_count = 14
    return {
        "enabled": (values.get(BACKUP_CONFIG_KEYS["enabled"]) or "true").strip().lower() == "true",
        "time": (values.get(BACKUP_CONFIG_KEYS["time"]) or "03:30").strip(),
        "retention_count": retention_count,
        "host_dir": (values.get(BACKUP_CONFIG_KEYS["host_dir"]) or DEFAULT_BACKUP_CONFIG[BACKUP_CONFIG_KEYS["host_dir"]]).strip(),
        "container_dir": (
            values.get(BACKUP_CONFIG_KEYS["container_dir"])
            or DEFAULT_BACKUP_CONFIG[BACKUP_CONFIG_KEYS["container_dir"]]
        ).strip(),
    }


def _format_size(size: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size} B"


def _list_backup_files(container_dir: str) -> list[dict[str, object]]:
    backup_dir = Path(container_dir)
    if not backup_dir.exists() or not backup_dir.is_dir():
        return []
    files: list[dict[str, object]] = []
    for path in backup_dir.glob("eastman-adms-backup-*.tar.gz"):
        if not BACKUP_FILE_RE.fullmatch(path.name):
            continue
        stat = path.stat()
        created_at = datetime.fromtimestamp(stat.st_mtime, DUBAI_TZ)
        files.append(
            {
                "filename": path.name,
                "size_bytes": stat.st_size,
                "size": _format_size(stat.st_size),
                "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S (UTC+4)"),
                "download_url": f"/settings/backup/download/{path.name}",
            }
        )
    return sorted(files, key=lambda item: str(item["filename"]), reverse=True)


def _payload() -> dict[str, object]:
    config = _backup_config()
    backups = _list_backup_files(str(config["container_dir"]))
    return {
        "config": config,
        "backups": backups,
        "latest_backup": backups[0] if backups else None,
        "backup_count": len(backups),
        "server_time": datetime.now(DUBAI_TZ).strftime("%Y-%m-%d %H:%M:%S (UTC+4)"),
        "commands": {
            "manual_backup": "bash scripts/DT015_backup_create.sh",
            "install_schedule": "bash scripts/DT015_backup_cron_install.sh",
            "restore": "bash scripts/DT015_backup_restore.sh /path/to/eastman-adms-backup-YYYYMMDD_HHMMSS.tar.gz",
            "server_path": "cd /opt/eastman/Eastman-adms-server",
        },
    }


@router.get("/settings/backup", response_class=HTMLResponse)
def backup_page(request: Request):
    return templates.TemplateResponse("backup.html", {"request": request, "data": _payload()})


@router.get("/api/settings/backup")
def backup_data() -> JSONResponse:
    return JSONResponse(_payload())


@router.post("/api/settings/backup")
def save_backup_config(payload: BackupConfigRequest) -> dict[str, object]:
    values = {
        BACKUP_CONFIG_KEYS["enabled"]: "true" if payload.enabled else "false",
        BACKUP_CONFIG_KEYS["time"]: payload.time,
        BACKUP_CONFIG_KEYS["retention_count"]: str(payload.retention_count),
        BACKUP_CONFIG_KEYS["host_dir"]: payload.host_dir,
        BACKUP_CONFIG_KEYS["container_dir"]: payload.container_dir,
    }
    os.environ.update(values)
    db_saved = save_config_values(values)
    file_result = _save_values_to_env_file(values)
    return {
        "saved": bool(db_saved or file_result["saved"]),
        "runtime_effective": True,
        "db_saved": db_saved,
        "env_file_saved": file_result["saved"],
        "env_file_path": file_result["path"],
        "restart_required": True,
        "message": "Backup configuration saved. Reinstall the cron schedule after changing backup time.",
        "data": _payload(),
    }


@router.get("/settings/backup/download/{filename}")
def download_backup(filename: str):
    if not BACKUP_FILE_RE.fullmatch(filename):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup file not found.")
    container_dir = str(_backup_config()["container_dir"])
    backup_path = Path(container_dir) / filename
    if not backup_path.exists() or not backup_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup file not found.")
    return FileResponse(
        path=str(backup_path),
        filename=filename,
        media_type="application/gzip",
    )
