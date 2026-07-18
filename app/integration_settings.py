from datetime import UTC, datetime
import json
import os
from pathlib import Path
import secrets
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request as UrlRequest, urlopen

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator

from sqlalchemy import text

from app.database import SessionLocal
from app.integration_config import get_config_values, save_config_values
from app.mingdao_attendance import attendance_sync_status_summary, sync_pending_attendance_to_mingdao
from app.mingdao_users import DEFAULT_TOKEN_VALUES, get_mingdao_api_runtime_state

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


def _normalize_openapi_url(value: str) -> str:
    replacements = {
        "\u200b": "",
        "\u200c": "",
        "\u200d": "",
        "\ufeff": "",
        "：": ":",
        "﹕": ":",
        "／": "/",
        "．": ".",
        "。": ".",
    }
    normalized = value.strip()
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return "".join(normalized.split())


class TokenSaveRequest(BaseModel):
    token: str = Field(min_length=32, max_length=255)


class AttendanceIntegrationConfigRequest(BaseModel):
    enabled: bool = False
    openapi_url: str = Field(max_length=1000)
    app_key: str = Field(max_length=255)
    sign: str = Field(max_length=255)
    worksheet_id: str = Field(max_length=128)
    employee_record_id_field_id: str = Field(max_length=128)
    check_time_field_id: str = Field(max_length=128)
    device_name_field_id: str = Field(max_length=128)
    device_sn_field_id: str = Field(max_length=128)
    retry_failed_after_minutes: int = Field(default=60, ge=1, le=10080)

    @field_validator(
        "app_key",
        "sign",
        "worksheet_id",
        "employee_record_id_field_id",
        "check_time_field_id",
        "device_name_field_id",
        "device_sn_field_id",
    )
    @classmethod
    def clean_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("openapi_url")
    @classmethod
    def clean_openapi_url(cls, value: str) -> str:
        return _normalize_openapi_url(value)


ATTENDANCE_CONFIG_KEYS = {
    "enabled": "MINGDAO_ATTENDANCE_SYNC_ENABLED",
    "openapi_url": "MINGDAO_ATTENDANCE_OPENAPI_URL",
    "app_key": "MINGDAO_ATTENDANCE_APP_KEY",
    "sign": "MINGDAO_ATTENDANCE_SIGN",
    "worksheet_id": "MINGDAO_ATTENDANCE_WORKSHEET_ID",
    "employee_record_id_field_id": "MINGDAO_ATTENDANCE_FIELD_EMPLOYEE_RECORD_ID",
    "check_time_field_id": "MINGDAO_ATTENDANCE_FIELD_CHECK_TIME",
    "device_name_field_id": "MINGDAO_ATTENDANCE_FIELD_DEVICE_NAME",
    "device_sn_field_id": "MINGDAO_ATTENDANCE_FIELD_DEVICE_SN",
    "retry_failed_after_minutes": "MINGDAO_ATTENDANCE_RETRY_FAILED_AFTER_MINUTES",
}

ATTENDANCE_TEST_STATE: dict[str, str | None] = {
    "last_test_time": None,
    "last_test_result": "Not Tested",
}


def _current_token() -> str:
    return os.getenv("MINGDAO_API_TOKEN", "").strip()


def _is_auth_enabled(token: str) -> bool:
    return token.lower() not in DEFAULT_TOKEN_VALUES


def _mask_token(token: str) -> str:
    if not token:
        return "Not Configured"
    return "*" * max(len(token), 32)


def _api_base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/") + "/api/v1"


def _server_time() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _health_status() -> dict[str, str]:
    token = _current_token()
    database_status = "Connected"
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
    except Exception as exc:
        database_status = f"Error: {exc}"
    return {
        "api": "Running",
        "database": database_status,
        "authentication": "Enabled" if _is_auth_enabled(token) else "Disabled",
        "ready": "Ready" if _is_auth_enabled(token) and database_status == "Connected" else "Token or Database Required",
    }


def _attendance_config() -> dict[str, object]:
    token = _current_token()
    stored_values = get_config_values(list(ATTENDANCE_CONFIG_KEYS.values()))
    sign = stored_values[ATTENDANCE_CONFIG_KEYS["sign"]].strip()
    configured_fields = {
        "Employee Record ID": stored_values[ATTENDANCE_CONFIG_KEYS["employee_record_id_field_id"]].strip(),
        "Check Time": stored_values[ATTENDANCE_CONFIG_KEYS["check_time_field_id"]].strip(),
        "Device Name": stored_values[ATTENDANCE_CONFIG_KEYS["device_name_field_id"]].strip(),
        "Device SN": stored_values[ATTENDANCE_CONFIG_KEYS["device_sn_field_id"]].strip(),
    }
    return {
        "enabled": stored_values[ATTENDANCE_CONFIG_KEYS["enabled"]].strip().lower() == "true",
        "openapi_url": stored_values[ATTENDANCE_CONFIG_KEYS["openapi_url"]].strip(),
        "app_key": stored_values[ATTENDANCE_CONFIG_KEYS["app_key"]].strip(),
        "sign": sign,
        "sign_masked": _mask_token(sign),
        "worksheet_id": stored_values[ATTENDANCE_CONFIG_KEYS["worksheet_id"]].strip(),
        "token_status": "ADMS API Token Configured" if _is_auth_enabled(token) else "ADMS API Token Not Configured",
        "configured_fields": configured_fields,
        "retry_failed_after_minutes": int(
            stored_values[ATTENDANCE_CONFIG_KEYS["retry_failed_after_minutes"]].strip() or "60"
        ),
        "last_test_time": ATTENDANCE_TEST_STATE["last_test_time"] or "-",
        "last_test_result": ATTENDANCE_TEST_STATE["last_test_result"] or "Not Tested",
        "sync_status": attendance_sync_status_summary(),
    }


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


def _save_token_to_env_file(token: str) -> dict[str, object]:
    return _save_values_to_env_file({"MINGDAO_API_TOKEN": token})


def _save_attendance_config_to_env_file(payload: AttendanceIntegrationConfigRequest) -> dict[str, object]:
    values = {
        ATTENDANCE_CONFIG_KEYS["enabled"]: "true" if payload.enabled else "false",
        ATTENDANCE_CONFIG_KEYS["openapi_url"]: payload.openapi_url,
        ATTENDANCE_CONFIG_KEYS["app_key"]: payload.app_key,
        ATTENDANCE_CONFIG_KEYS["sign"]: payload.sign,
        ATTENDANCE_CONFIG_KEYS["worksheet_id"]: payload.worksheet_id,
        ATTENDANCE_CONFIG_KEYS["employee_record_id_field_id"]: payload.employee_record_id_field_id,
        ATTENDANCE_CONFIG_KEYS["check_time_field_id"]: payload.check_time_field_id,
        ATTENDANCE_CONFIG_KEYS["device_name_field_id"]: payload.device_name_field_id,
        ATTENDANCE_CONFIG_KEYS["device_sn_field_id"]: payload.device_sn_field_id,
        ATTENDANCE_CONFIG_KEYS["retry_failed_after_minutes"]: str(payload.retry_failed_after_minutes),
    }
    os.environ.update(values)
    db_saved = save_config_values(values)
    file_result = _save_values_to_env_file(values)
    return {
        "saved": bool(db_saved or file_result["saved"]),
        "db_saved": db_saved,
        "env_file_saved": file_result["saved"],
        "path": file_result["path"],
    }


def _validate_attendance_config(payload: AttendanceIntegrationConfigRequest) -> list[str]:
    errors: list[str] = []
    token = _current_token()
    parsed_url = urlparse(payload.openapi_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        errors.append("OpenAPI URL must be a valid http or https URL.")
    if not payload.app_key:
        errors.append("AppKey is required.")
    if not payload.sign:
        errors.append("Sign is required.")
    if not payload.worksheet_id:
        errors.append("Worksheet ID is required.")
    if not _is_auth_enabled(token):
        errors.append("ADMS API Token is not configured.")
    required_fields = {
        "Employee Record ID": payload.employee_record_id_field_id,
        "Check Time": payload.check_time_field_id,
        "Device Name": payload.device_name_field_id,
        "Device SN": payload.device_sn_field_id,
    }
    for label, value in required_fields.items():
        if not value:
            errors.append(f"{label} target field ID is required.")
    return errors


def _attendance_schema_url(openapi_url: str, worksheet_id: str) -> str:
    cleaned_url = openapi_url.rstrip("/")
    encoded_worksheet_id = quote(worksheet_id.strip(), safe="")
    if "{worksheet_id}" in cleaned_url:
        return cleaned_url.replace("{worksheet_id}", encoded_worksheet_id)
    if "/v3/app/worksheets/" in cleaned_url:
        before_rows = cleaned_url.split("/rows", 1)[0]
        if before_rows != cleaned_url:
            return before_rows
        return cleaned_url
    return f"{cleaned_url}/v3/app/worksheets/{encoded_worksheet_id}"


def _test_attendance_connection(payload: AttendanceIntegrationConfigRequest) -> dict[str, object]:
    errors = _validate_attendance_config(payload)
    if errors:
        return {"success": False, "message": "Validation failed.", "errors": errors}

    schema_url = _attendance_schema_url(payload.openapi_url, payload.worksheet_id)
    request = UrlRequest(
        schema_url,
        headers={
            "HAP-Appkey": payload.app_key,
            "HAP-Sign": payload.sign,
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=10) as response:
            response_status = response.status
            response_body = response.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {
            "success": False,
            "message": f"Mingdao OpenAPI returned HTTP {exc.code}.",
            "errors": [body or exc.reason],
            "schema_url": schema_url,
        }
    except URLError as exc:
        return {
            "success": False,
            "message": "Mingdao OpenAPI connection failed.",
            "errors": [str(exc.reason)],
            "schema_url": schema_url,
        }
    except Exception as exc:
        return {
            "success": False,
            "message": "Mingdao OpenAPI test failed.",
            "errors": [str(exc)],
            "schema_url": schema_url,
        }

    try:
        response_json = json.loads(response_body)
    except json.JSONDecodeError:
        return {
            "success": False,
            "message": "Mingdao OpenAPI did not return JSON.",
            "errors": [response_body[:500]],
            "schema_url": schema_url,
            "http_status": response_status,
        }

    if response_json.get("success") is False:
        return {
            "success": False,
            "message": "Mingdao OpenAPI returned success=false.",
            "errors": [response_json.get("error_msg") or response_json.get("message") or "Unknown error"],
            "schema_url": schema_url,
            "http_status": response_status,
        }

    data = response_json.get("data") or {}
    field_ids = _collect_field_ids(data)
    required_field_ids = {
        "Employee Record ID": payload.employee_record_id_field_id,
        "Check Time": payload.check_time_field_id,
        "Device Name": payload.device_name_field_id,
        "Device SN": payload.device_sn_field_id,
    }
    missing_fields = [label for label, field_id in required_field_ids.items() if field_id not in field_ids]
    if missing_fields:
        return {
            "success": False,
            "message": "Worksheet reached, but configured field IDs were not found.",
            "errors": [", ".join(missing_fields)],
            "schema_url": schema_url,
            "http_status": response_status,
            "worksheet_name": data.get("name") or "-",
        }

    return {
        "success": True,
        "message": "Attendance synchronization connection test succeeded.",
        "errors": [],
        "schema_url": schema_url,
        "http_status": response_status,
        "worksheet_name": data.get("name") or "-",
        "field_count": len(field_ids),
    }


def _collect_field_ids(value: object) -> set[str]:
    field_ids: set[str] = set()
    if isinstance(value, dict):
        field_id = value.get("id") or value.get("controlId") or value.get("fieldId")
        if field_id:
            field_ids.add(str(field_id))
        for child in value.values():
            field_ids.update(_collect_field_ids(child))
    elif isinstance(value, list):
        for item in value:
            field_ids.update(_collect_field_ids(item))
    return field_ids


def _collect_error_tokens(value: object) -> list[dict[str, str]]:
    tokens: list[dict[str, str]] = []
    if isinstance(value, dict):
        field_id = value.get("controlId") or value.get("control_id") or value.get("fieldId") or value.get("field_id")
        field_name = value.get("controlName") or value.get("fieldName") or value.get("name") or value.get("title")
        message = value.get("error_msg") or value.get("message") or value.get("msg")
        if field_id or field_name or message:
            tokens.append(
                {
                    "field_id": str(field_id or ""),
                    "field_name": str(field_name or ""),
                    "message": str(message or ""),
                }
            )
        for child in value.values():
            tokens.extend(_collect_error_tokens(child))
    elif isinstance(value, list):
        for item in value:
            tokens.extend(_collect_error_tokens(item))
    return tokens


def _attendance_field_name_by_id() -> dict[str, str]:
    config = _attendance_config()
    fields = config.get("configured_fields", {})
    if not isinstance(fields, dict):
        return {}
    return {
        str(field_id): f"{label} / {zh_label}"
        for label, zh_label, field_id in (
            ("Employee Record ID", "员工记录ID字段", fields.get("Employee Record ID")),
            ("Check Time", "考勤时间字段", fields.get("Check Time")),
            ("Device Name", "设备名称字段", fields.get("Device Name")),
            ("Device SN", "设备序列号字段", fields.get("Device SN")),
        )
        if field_id
    }


def _mingdao_error_detail(
    last_error: str | None,
    response_body: str | None,
    field_name_by_id: dict[str, str],
) -> dict[str, object]:
    details: list[str] = []
    field_names: list[str] = []
    if last_error:
        details.append(last_error)
    if response_body:
        try:
            response_json = json.loads(response_body)
            tokens = _collect_error_tokens(response_json)
            if tokens:
                for token in tokens[:12]:
                    field_id = token.get("field_id", "")
                    field_name = token.get("field_name") or field_name_by_id.get(field_id) or field_id
                    if field_name:
                        field_names.append(field_name)
                    if token.get("message"):
                        details.append(token["message"])
            response_text = json.dumps(response_json, ensure_ascii=False)
            for field_id, configured_name in field_name_by_id.items():
                if field_id in response_text:
                    field_names.append(configured_name)
            if isinstance(response_json, dict) and response_json.get("data") is not None:
                details.append(f"data: {response_json['data']}")
        except Exception:
            details.append(response_body[:500])
    if response_body and not field_names and "controlId" in response_body:
        field_names.append("Unknown Mingdao required field / 明道返回未包含字段名称")

    def unique(values: list[str]) -> list[str]:
        seen: set[str] = set()
        unique_values: list[str] = []
        for item in values:
            text_value = str(item)
            if text_value and text_value not in seen:
                unique_values.append(text_value)
                seen.add(text_value)
        return unique_values

    return {
        "field_names": unique(field_names),
        "message": "\n".join(unique(details)),
    }


def _integration_payload(request: Request, *, show_token: bool = False) -> dict[str, object]:
    token = _current_token()
    runtime = get_mingdao_api_runtime_state()
    health = _health_status()
    return {
        "system_name": "Mingdao",
        "status": "Enabled" if _is_auth_enabled(token) else "Disabled",
        "api_base_url": _api_base_url(request),
        "authentication": "Bearer Token",
        "token_masked": _mask_token(token),
        "token_value": token if show_token else "",
        "server_time": _server_time(),
        "api_status": health["api"],
        "authentication_status": health["authentication"],
        "last_api_request_time": runtime.get("last_request_time") or "No API requests have been received.",
        "last_caller_ip": runtime.get("last_caller_ip") or "-",
        "last_api_response_code": runtime.get("last_response_code") or "-",
        "total_api_requests": runtime.get("total_requests") or 0,
        "health": health,
        "attendance_sync": _attendance_config(),
    }


@router.get("/settings/integration", response_class=HTMLResponse)
def integration_page(request: Request):
    return templates.TemplateResponse(
        "integration.html",
        {"request": request, "data": _integration_payload(request), "page_mode": "inbound"},
    )


@router.get("/settings/attendance-sync", response_class=HTMLResponse)
def attendance_sync_page(request: Request):
    return templates.TemplateResponse(
        "integration.html",
        {"request": request, "data": _integration_payload(request), "page_mode": "attendance"},
    )


@router.get("/api/settings/integration")
def integration_data(request: Request, show_token: bool = False) -> JSONResponse:
    return JSONResponse(_integration_payload(request, show_token=show_token))


@router.post("/api/settings/integration/token/generate")
def generate_token() -> dict[str, str]:
    return {"token": secrets.token_urlsafe(36)}


@router.post("/api/settings/integration/token/save")
def save_token(payload: TokenSaveRequest) -> dict[str, object]:
    token = payload.token.strip()
    if len(token) < 32:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Token must be at least 32 characters.")
    os.environ["MINGDAO_API_TOKEN"] = token
    file_result = _save_token_to_env_file(token)
    return {
        "saved": True,
        "runtime_effective": True,
        "env_file_saved": file_result["saved"],
        "env_file_path": file_result["path"],
        "restart_required": True,
        "message": "API service restart is required before the new token becomes effective for future container restarts.",
    }


@router.post("/api/settings/integration/attendance")
def save_attendance_config(payload: AttendanceIntegrationConfigRequest) -> dict[str, object]:
    errors = _validate_attendance_config(payload)
    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=errors)
    file_result = _save_attendance_config_to_env_file(payload)
    return {
        "saved": True,
        "runtime_effective": True,
        "db_saved": file_result["db_saved"],
        "env_file_saved": file_result["env_file_saved"],
        "env_file_path": file_result["path"],
        "restart_required": True,
        "message": "Attendance synchronization configuration saved. DT014 will read this configuration.",
        "attendance_sync": _attendance_config(),
    }


@router.post("/api/settings/integration/attendance/test")
def test_attendance_config(payload: AttendanceIntegrationConfigRequest) -> dict[str, object]:
    result = _test_attendance_connection(payload)
    ATTENDANCE_TEST_STATE["last_test_time"] = _server_time()
    ATTENDANCE_TEST_STATE["last_test_result"] = "Success" if result["success"] else f"Failed: {result['message']}"
    return result | {
        "last_test_time": ATTENDANCE_TEST_STATE["last_test_time"],
        "last_test_result": ATTENDANCE_TEST_STATE["last_test_result"],
    }


@router.post("/api/settings/integration/attendance/sync")
def sync_attendance_now(limit: int = 50) -> dict[str, object]:
    return sync_pending_attendance_to_mingdao(limit=limit)


@router.get("/api/settings/integration/attendance/sync-log")
def attendance_sync_log(limit: int = 50) -> dict[str, object]:
    safe_limit = max(1, min(limit, 200))
    with SessionLocal() as session:
        rows = session.execute(
            text(
                """
                SELECT
                    ams.id AS sync_id,
                    ams.attendance_event_id,
                    ams.sync_status,
                    ams.mingdao_row_id,
                    ams.retry_count,
                    ams.last_error,
                    ams.response_body,
                    ams.last_sync_time,
                    ae.device_sn,
                    ae.pin,
                    ae.attendance_time,
                    du.employee_id,
                    du.employee_record_id,
                    du.name,
                    du.department
                FROM attendance_mingdao_sync ams
                JOIN attendance_event ae ON ae.id = ams.attendance_event_id
                LEFT JOIN device_user du ON du.pin = ae.pin
                ORDER BY ae.attendance_time DESC, ams.updated_at DESC, ams.id DESC
                LIMIT :limit
                """
            ),
            {"limit": safe_limit},
        ).mappings()
        field_name_by_id = _attendance_field_name_by_id()
        items: list[dict[str, object]] = []
        for row in rows:
            item = dict(row)
            error_detail = _mingdao_error_detail(
                item.get("last_error"),
                item.get("response_body"),
                field_name_by_id,
            )
            item["error_field_names"] = error_detail["field_names"]
            item["error_detail"] = error_detail["message"]
            item.pop("response_body", None)
            items.append(item)
        return {"items": items}


@router.get("/api/settings/integration/health")
def integration_health() -> dict[str, str]:
    return _health_status()


@router.get("/settings/integration/documentation", response_class=PlainTextResponse)
def integration_documentation() -> str:
    document_path = Path(__file__).resolve().parents[1] / "docs" / "Mingdao_API_Integration.md"
    if not document_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration documentation not found.")
    return document_path.read_text(encoding="utf-8")
