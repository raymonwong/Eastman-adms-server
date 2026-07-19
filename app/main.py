import asyncio
from contextlib import asynccontextmanager
from contextlib import suppress
from datetime import UTC, datetime

from fastapi import FastAPI

from app.adms import router as adms_router
from app.alert_settings import alert_check_interval_seconds, process_alert_notifications
from app.alert_settings import router as alert_settings_router
from app.backup_settings import router as backup_settings_router
from app.console import router as console_router
from app.database import check_database_connection, configure_session_factory, create_database_engine, create_database_tables
from app.device_management import router as device_management_router
from app.help_center import router as help_center_router
from app.integration_settings import router as integration_settings_router
from app.mingdao_attendance import attendance_auto_sync_interval_seconds, sync_pending_attendance_to_mingdao
from app.mingdao_users import router as mingdao_users_router
from app.user_console import router as user_console_router
from app.user_reconciliation import run_due_user_reconciliation, user_reconciliation_check_interval_seconds
from app.settings import Settings

settings = Settings.from_env()
engine = create_database_engine(settings)
configure_session_factory(engine)


async def _attendance_sync_loop() -> None:
    await asyncio.sleep(attendance_auto_sync_interval_seconds())
    while True:
        try:
            result = await asyncio.to_thread(sync_pending_attendance_to_mingdao)
            if result.get("uploaded") or result.get("failed"):
                print(
                    "Mingdao Attendance Sync",
                    f"uploaded={result.get('uploaded', 0)}",
                    f"failed={result.get('failed', 0)}",
                    f"pending={result.get('status', {}).get('PENDING', 0)}",
                    flush=True,
                )
        except Exception as exc:
            print(f"Mingdao Attendance Sync Error: {exc}", flush=True)
        await asyncio.sleep(attendance_auto_sync_interval_seconds())


async def _user_reconciliation_loop() -> None:
    await asyncio.sleep(user_reconciliation_check_interval_seconds())
    while True:
        try:
            result = await asyncio.to_thread(run_due_user_reconciliation)
            if result:
                print(
                    "User Reconciliation",
                    f"sync_records={result.get('sync_records', 0)}",
                    f"last_run_at={result.get('last_run_at', '-')}",
                    flush=True,
                )
        except Exception as exc:
            print(f"User Reconciliation Error: {exc}", flush=True)
        await asyncio.sleep(user_reconciliation_check_interval_seconds())


async def _alert_notification_loop() -> None:
    await asyncio.sleep(alert_check_interval_seconds())
    while True:
        try:
            result = await asyncio.to_thread(process_alert_notifications)
            if result.get("sent_count") or result.get("critical_count") or result.get("warning_count"):
                print(
                    "ADMS Alert Check",
                    f"alerts={result.get('alert_count', 0)}",
                    f"critical={result.get('critical_count', 0)}",
                    f"warning={result.get('warning_count', 0)}",
                    f"sent={result.get('sent_count', 0)}",
                    flush=True,
                )
        except Exception as exc:
            print(f"ADMS Alert Check Error: {exc}", flush=True)
        await asyncio.sleep(alert_check_interval_seconds())


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Fail fast during startup if MySQL is unavailable, then prepare DT002 tables.
    check_database_connection(engine)
    print("========================================", flush=True)
    print("Database Connected", flush=True)
    print("Checking Tables...", flush=True)
    create_database_tables(engine)
    print("Tables Ready", flush=True)
    print("========================================", flush=True)
    attendance_sync_task = asyncio.create_task(_attendance_sync_loop())
    user_reconciliation_task = asyncio.create_task(_user_reconciliation_loop())
    alert_notification_task = asyncio.create_task(_alert_notification_loop())
    try:
        yield
    finally:
        attendance_sync_task.cancel()
        user_reconciliation_task.cancel()
        alert_notification_task.cancel()
        with suppress(asyncio.CancelledError):
            await attendance_sync_task
        with suppress(asyncio.CancelledError):
            await user_reconciliation_task
        with suppress(asyncio.CancelledError):
            await alert_notification_task


app = FastAPI(title=settings.app_name, version="0.0.2", lifespan=lifespan)
app.include_router(adms_router)
app.include_router(alert_settings_router)
app.include_router(backup_settings_router)
app.include_router(console_router)
app.include_router(device_management_router)
app.include_router(help_center_router)
app.include_router(integration_settings_router)
app.include_router(mingdao_users_router)
app.include_router(user_console_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/health")
def api_health() -> dict[str, str]:
    check_database_connection(engine)
    return {
        "project": settings.project_name,
        "version": "0.0.2",
        "status": "running",
        "database": "connected",
        "time": datetime.now(UTC).isoformat(),
    }


@app.get("/ready")
def ready() -> dict[str, str]:
    check_database_connection(engine)
    return {"status": "ok"}
