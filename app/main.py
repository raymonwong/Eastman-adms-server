from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI

from app.database import check_database_connection, create_database_engine, create_database_tables
from app.settings import Settings

settings = Settings.from_env()
engine = create_database_engine(settings)


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
    yield


app = FastAPI(title=settings.app_name, version="0.0.2", lifespan=lifespan)


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
