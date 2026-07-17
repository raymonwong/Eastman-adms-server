from datetime import UTC, datetime
import os
from pathlib import Path
import secrets

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from sqlalchemy import text

from app.database import SessionLocal
from app.mingdao_users import DEFAULT_TOKEN_VALUES, get_mingdao_api_runtime_state

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


class TokenSaveRequest(BaseModel):
    token: str = Field(min_length=32, max_length=255)


def _current_token() -> str:
    return os.getenv("MINGDAO_API_TOKEN", "").strip()


def _is_auth_enabled(token: str) -> bool:
    return token.lower() not in DEFAULT_TOKEN_VALUES


def _mask_token(token: str) -> str:
    if not token:
        return "Not Configured"
    if len(token) <= 8:
        return "*" * len(token)
    return f"{token[:4]}{'*' * 12}{token[-4:]}"


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


def _env_file_candidates() -> list[Path]:
    candidates: list[Path] = []
    configured = os.getenv("ENV_FILE")
    if configured:
        candidates.append(Path(configured))
    candidates.extend([Path.cwd() / ".env", Path("/app/.env")])
    return candidates


def _save_token_to_env_file(token: str) -> dict[str, object]:
    for path in _env_file_candidates():
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        updated = False
        next_lines: list[str] = []
        for line in lines:
            if line.startswith("MINGDAO_API_TOKEN="):
                next_lines.append(f"MINGDAO_API_TOKEN={token}")
                updated = True
            else:
                next_lines.append(line)
        if not updated:
            next_lines.append(f"MINGDAO_API_TOKEN={token}")
        path.write_text("\n".join(next_lines) + "\n", encoding="utf-8")
        return {"saved": True, "path": str(path)}
    return {"saved": False, "path": ""}


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
        "health": health,
    }


@router.get("/settings/integration", response_class=HTMLResponse)
def integration_page(request: Request):
    return templates.TemplateResponse("integration.html", {"request": request, "data": _integration_payload(request)})


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


@router.get("/api/settings/integration/health")
def integration_health() -> dict[str, str]:
    return _health_status()
