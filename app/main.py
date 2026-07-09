from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import check_database_connection, create_database_engine
from app.settings import Settings

settings = Settings.from_env()
engine = create_database_engine(settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Fail fast during startup if MySQL is unavailable.
    check_database_connection(engine)
    yield


app = FastAPI(title=settings.app_name, version="DT001", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    check_database_connection(engine)
    return {"status": "ok"}
