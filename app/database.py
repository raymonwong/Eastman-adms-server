from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.models import Base
from app.settings import Settings


def create_database_engine(settings: Settings) -> Engine:
    # pool_pre_ping avoids stale MySQL connections after container restarts.
    return create_engine(settings.database_url(), pool_pre_ping=True)


def check_database_connection(engine: Engine) -> None:
    # SELECT 1 keeps the startup check lightweight and database-agnostic.
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def create_database_tables(engine: Engine) -> None:
    # SQLAlchemy create_all is idempotent and only creates tables that do not exist.
    Base.metadata.create_all(bind=engine)
