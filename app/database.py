from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.settings import Settings


def create_database_engine(settings: Settings) -> Engine:
    # pool_pre_ping avoids stale MySQL connections after container restarts.
    return create_engine(settings.database_url(), pool_pre_ping=True)


def check_database_connection(engine: Engine) -> None:
    # DT001 intentionally does not create tables; SELECT 1 only verifies MySQL connectivity.
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
