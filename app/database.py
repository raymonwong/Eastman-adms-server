from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.settings import Settings


SessionLocal = sessionmaker(autoflush=False, autocommit=False)


def create_database_engine(settings: Settings) -> Engine:
    # pool_pre_ping avoids stale MySQL connections after container restarts.
    return create_engine(settings.database_url(), pool_pre_ping=True)


def configure_session_factory(engine: Engine) -> None:
    SessionLocal.configure(bind=engine)


def check_database_connection(engine: Engine) -> None:
    # SELECT 1 keeps the startup check lightweight and database-agnostic.
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def create_database_tables(engine: Engine) -> None:
    # SQLAlchemy create_all is idempotent and only creates tables that do not exist.
    Base.metadata.create_all(bind=engine)
    ensure_dt003_columns(engine)


def ensure_dt003_columns(engine: Engine) -> None:
    # DT003 runs before Alembic exists, so add only the new ingress columns if missing.
    statements = (
        "ALTER TABLE device ADD COLUMN first_online DATETIME NULL",
        "ALTER TABLE device ADD COLUMN status VARCHAR(32) NULL",
        "ALTER TABLE raw_request ADD COLUMN request_url TEXT NULL",
        "ALTER TABLE raw_request ADD COLUMN query_params TEXT NULL",
        "ALTER TABLE raw_request ADD COLUMN client_ip VARCHAR(45) NULL",
        "ALTER TABLE raw_request ADD COLUMN user_agent TEXT NULL",
        "ALTER TABLE raw_request ADD COLUMN content_type TEXT NULL",
        "ALTER TABLE raw_request ADD COLUMN response_body TEXT NULL",
        "ALTER TABLE raw_request ADD COLUMN response_status_code INT NULL",
        "ALTER TABLE raw_request ADD COLUMN request_size INT NULL",
        "ALTER TABLE raw_request ADD COLUMN response_size INT NULL",
        "ALTER TABLE raw_request ADD COLUMN parsed BOOL NOT NULL DEFAULT 0",
        "ALTER TABLE raw_request ADD COLUMN request_hash VARCHAR(64) NULL",
        "CREATE INDEX ix_raw_request_request_hash ON raw_request (request_hash)",
        """
        CREATE TABLE IF NOT EXISTS device_event_log (
            id INT NOT NULL AUTO_INCREMENT,
            event_type VARCHAR(32) NOT NULL,
            device_sn VARCHAR(64) NULL,
            device_id INT NULL,
            client_ip VARCHAR(45) NULL,
            connect_time DATETIME NOT NULL,
            method VARCHAR(16) NOT NULL,
            url TEXT NOT NULL,
            status_code INT NOT NULL,
            response TEXT NOT NULL,
            user_agent TEXT NULL,
            request_hash VARCHAR(64) NOT NULL,
            remark TEXT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            CONSTRAINT fk_device_event_log_device_id FOREIGN KEY (device_id) REFERENCES device(id)
        )
        """,
        "CREATE INDEX ix_device_event_log_device_sn ON device_event_log (device_sn)",
        "CREATE INDEX ix_device_event_log_connect_time ON device_event_log (connect_time)",
        "CREATE INDEX ix_device_event_log_request_hash ON device_event_log (request_hash)",
    )

    with engine.begin() as connection:
        for statement in statements:
            try:
                connection.execute(text(statement))
            except Exception as exc:
                error_text = str(exc).lower()
                if (
                    "duplicate column" in error_text
                    or "duplicate key name" in error_text
                    or "already exists" in error_text
                ):
                    continue
                raise
