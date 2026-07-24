import base64
import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path
from urllib.parse import parse_qs, quote

from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.integration_config import get_config_value, save_config_values


AUTH_COOKIE_NAME = "adms_console_session"
ADMIN_PASSWORD_HASH_KEY = "CONSOLE_ADMIN_PASSWORD_HASH"
DEFAULT_ADMIN_PASSWORD = "admin"
DEFAULT_SESSION_TTL_SECONDS = 12 * 60 * 60

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
router = APIRouter()


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _session_secret() -> str:
    return (
        os.getenv("CONSOLE_SESSION_SECRET")
        or os.getenv("MINGDAO_API_TOKEN")
        or os.getenv("MYSQL_PASSWORD")
        or "eastman-adms-console-dev-secret"
    )


def _session_ttl_seconds() -> int:
    raw_value = os.getenv("CONSOLE_SESSION_TTL_SECONDS", str(DEFAULT_SESSION_TTL_SECONDS))
    try:
        value = int(raw_value)
    except ValueError:
        return DEFAULT_SESSION_TTL_SECONDS
    return max(300, value)


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 260000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${_b64encode(digest)}"


def _verify_hash(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt, expected_digest = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
        return hmac.compare_digest(_b64encode(digest), expected_digest)
    except Exception:
        return False


def verify_admin_password(password: str) -> bool:
    stored_hash = get_config_value(ADMIN_PASSWORD_HASH_KEY, "")
    if stored_hash:
        return _verify_hash(password, stored_hash)

    env_hash = os.getenv(ADMIN_PASSWORD_HASH_KEY, "")
    if env_hash:
        return _verify_hash(password, env_hash)

    env_password = os.getenv("CONSOLE_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
    return hmac.compare_digest(password, env_password)


def save_admin_password(password: str) -> bool:
    return save_config_values({ADMIN_PASSWORD_HASH_KEY: _hash_password(password)})


def create_session_token() -> str:
    expires_at = str(int(time.time()) + _session_ttl_seconds())
    payload = _b64encode(f"admin|{expires_at}".encode("utf-8"))
    signature = hmac.new(_session_secret().encode("utf-8"), payload.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def verify_session_token(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    payload, signature = token.rsplit(".", 1)
    expected = hmac.new(_session_secret().encode("utf-8"), payload.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return False
    try:
        decoded = _b64decode(payload).decode("utf-8")
        username, expires_at_text = decoded.split("|", 1)
        return username == "admin" and int(expires_at_text) >= int(time.time())
    except Exception:
        return False


def _set_auth_cookie(response: Response) -> None:
    response.set_cookie(
        AUTH_COOKIE_NAME,
        create_session_token(),
        max_age=_session_ttl_seconds(),
        httponly=True,
        samesite="lax",
        secure=os.getenv("CONSOLE_COOKIE_SECURE", "false").lower() == "true",
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(AUTH_COOKIE_NAME)


def _is_public_path(path: str) -> bool:
    public_exact = {
        "/login",
        "/logout",
        "/health",
        "/ready",
        "/api/v1/health",
        "/settings/help",
        "/settings/user-guide",
        "/settings/device-setup-guide",
    }
    public_prefixes = (
        "/iclock/",
        "/api/v1/users",
        "/static/",
    )
    return path in public_exact or any(path.startswith(prefix) for prefix in public_prefixes)


def _safe_next_url(next_url: str | None) -> str:
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return "/console"


def _login_redirect(request: Request) -> RedirectResponse:
    target = request.url.path
    if request.url.query:
        target += f"?{request.url.query}"
    return RedirectResponse(url=f"/login?next={quote(target, safe='')}", status_code=status.HTTP_303_SEE_OTHER)


async def auth_middleware(request: Request, call_next):
    if _is_public_path(request.url.path) or verify_session_token(request.cookies.get(AUTH_COOKIE_NAME)):
        return await call_next(request)

    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Admin authentication required."}, status_code=status.HTTP_401_UNAUTHORIZED)
    return _login_redirect(request)


async def _read_form(request: Request) -> dict[str, str]:
    body = (await request.body()).decode("utf-8")
    values = parse_qs(body, keep_blank_values=True)
    return {key: value[0] if value else "" for key, value in values.items()}


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = "/console") -> HTMLResponse:
    next_url = _safe_next_url(next)
    if verify_session_token(request.cookies.get(AUTH_COOKIE_NAME)):
        return RedirectResponse(url=next_url, status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("login.html", {"request": request, "next_url": next_url, "error": ""})


@router.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request) -> Response:
    form = await _read_form(request)
    password = form.get("password", "")
    next_url = _safe_next_url(form.get("next", "/console"))
    if verify_admin_password(password):
        response = RedirectResponse(url=next_url, status_code=status.HTTP_303_SEE_OTHER)
        _set_auth_cookie(response)
        return response
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "next_url": next_url, "error": "Invalid admin password / 管理员密码不正确"},
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


@router.post("/logout")
async def logout() -> RedirectResponse:
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    _clear_auth_cookie(response)
    return response


@router.get("/settings/password", response_class=HTMLResponse)
async def password_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "password.html",
        {"request": request, "error": "", "success": ""},
    )


@router.post("/settings/password", response_class=HTMLResponse)
async def password_submit(request: Request) -> Response:
    form = await _read_form(request)
    current_password = form.get("current_password", "")
    new_password = form.get("new_password", "")
    confirm_password = form.get("confirm_password", "")
    error = ""
    success = ""

    if not verify_admin_password(current_password):
        error = "Current password is incorrect / 当前密码不正确"
    elif len(new_password) < 8:
        error = "New password must be at least 8 characters / 新密码至少 8 位"
    elif new_password != confirm_password:
        error = "Password confirmation does not match / 两次输入的新密码不一致"
    elif not save_admin_password(new_password):
        error = "Password could not be saved / 密码保存失败"
    else:
        success = "Admin password updated / 管理员密码已更新"

    response = templates.TemplateResponse(
        "password.html",
        {"request": request, "error": error, "success": success},
        status_code=status.HTTP_400_BAD_REQUEST if error else status.HTTP_200_OK,
    )
    if success:
        _set_auth_cookie(response)
    return response
