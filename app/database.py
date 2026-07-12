from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.settings import Settings


SessionLocal = sessionmaker(autoflush=False, autocommit=False, expire_on_commit=False)


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
    ensure_dt004_columns(engine)
    ensure_dt005_tables(engine)
    ensure_dt006_tables(engine)
    ensure_dt007_tables(engine)
    ensure_dt008_tables(engine)


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


def ensure_dt004_columns(engine: Engine) -> None:
    # DT004 adds handshake metadata to device without introducing a migration tool yet.
    statements = (
        "ALTER TABLE device ADD COLUMN last_handshake_time DATETIME NULL",
        "ALTER TABLE device ADD COLUMN push_version VARCHAR(32) NULL",
        "ALTER TABLE device ADD COLUMN device_type VARCHAR(32) NULL",
        "ALTER TABLE device ADD COLUMN language VARCHAR(32) NULL",
        "ALTER TABLE device ADD COLUMN push_options TEXT NULL",
    )

    with engine.begin() as connection:
        for statement in statements:
            try:
                connection.execute(text(statement))
            except Exception as exc:
                if "duplicate column" in str(exc).lower():
                    continue
                raise


def ensure_dt005_tables(engine: Engine) -> None:
    # DT005 introduces raw attendance events, separate from future attendance results.
    statements = (
        """
        CREATE TABLE IF NOT EXISTS attendance_event (
            id INT NOT NULL AUTO_INCREMENT,
            device_sn VARCHAR(64) NOT NULL,
            pin VARCHAR(64) NOT NULL,
            attendance_time DATETIME NOT NULL,
            status VARCHAR(32) NULL,
            verify VARCHAR(32) NOT NULL,
            work_code VARCHAR(64) NULL,
            reserved1 VARCHAR(255) NULL,
            reserved2 VARCHAR(255) NULL,
            mask_flag VARCHAR(32) NULL,
            temperature VARCHAR(32) NULL,
            conv_temperature VARCHAR(32) NULL,
            receive_time DATETIME NOT NULL,
            raw_request_id INT NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            CONSTRAINT fk_attendance_event_raw_request_id FOREIGN KEY (raw_request_id) REFERENCES raw_request(id),
            CONSTRAINT uq_attendance_event_device_pin_time_verify UNIQUE (device_sn, pin, attendance_time, verify)
        )
        """,
        "ALTER TABLE attendance_event ADD COLUMN mask_flag VARCHAR(32) NULL",
        "ALTER TABLE attendance_event ADD COLUMN temperature VARCHAR(32) NULL",
        "ALTER TABLE attendance_event ADD COLUMN conv_temperature VARCHAR(32) NULL",
        "CREATE INDEX ix_attendance_event_device_sn ON attendance_event (device_sn)",
        "CREATE INDEX ix_attendance_event_pin ON attendance_event (pin)",
        "CREATE INDEX ix_attendance_event_attendance_time ON attendance_event (attendance_time)",
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


def ensure_dt006_tables(engine: Engine) -> None:
    # DT006 introduces raw operation events uploaded through OPERLOG.
    statements = (
        """
        CREATE TABLE IF NOT EXISTS operation_event (
            id INT NOT NULL AUTO_INCREMENT,
            device_sn VARCHAR(64) NOT NULL,
            operation_code VARCHAR(32) NOT NULL,
            operation_name VARCHAR(128) NULL,
            operator VARCHAR(64) NULL,
            operation_time DATETIME NOT NULL,
            operation_object VARCHAR(128) NULL,
            value1 TEXT NULL,
            value2 TEXT NULL,
            value3 TEXT NULL,
            receive_time DATETIME NOT NULL,
            raw_request_id INT NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            CONSTRAINT fk_operation_event_raw_request_id FOREIGN KEY (raw_request_id) REFERENCES raw_request(id)
        )
        """,
        "CREATE INDEX ix_operation_event_device_sn ON operation_event (device_sn)",
        "CREATE INDEX ix_operation_event_operation_code ON operation_event (operation_code)",
        "CREATE INDEX ix_operation_event_operation_time ON operation_event (operation_time)",
    )

    with engine.begin() as connection:
        for statement in statements:
            try:
                connection.execute(text(statement))
            except Exception as exc:
                error_text = str(exc).lower()
                if "duplicate key name" in error_text or "already exists" in error_text:
                    continue
                raise


def ensure_dt007_tables(engine: Engine) -> None:
    # DT007 records per-device sync state without changing returned Stamp behavior yet.
    statements = (
        """
        CREATE TABLE IF NOT EXISTS device_sync_state (
            id INT NOT NULL AUTO_INCREMENT,
            device_sn VARCHAR(64) NOT NULL,
            data_type VARCHAR(32) NOT NULL,
            device_stamp VARCHAR(64) NULL,
            last_success_time DATETIME NULL,
            last_raw_request_id INT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            CONSTRAINT fk_device_sync_state_raw_request_id FOREIGN KEY (last_raw_request_id) REFERENCES raw_request(id),
            CONSTRAINT uq_device_sync_state_device_type UNIQUE (device_sn, data_type)
        )
        """,
        "CREATE INDEX ix_device_sync_state_device_sn ON device_sync_state (device_sn)",
        "CREATE INDEX ix_device_sync_state_data_type ON device_sync_state (data_type)",
    )

    with engine.begin() as connection:
        for statement in statements:
            try:
                connection.execute(text(statement))
            except Exception as exc:
                error_text = str(exc).lower()
                if "duplicate key name" in error_text or "already exists" in error_text:
                    continue
                raise


def ensure_dt008_tables(engine: Engine) -> None:
    # DT008 stores USER records that real devices upload inside OPERLOG bodies.
    statements = (
        """
        CREATE TABLE IF NOT EXISTS device_user (
            id INT NOT NULL AUTO_INCREMENT,
            device_sn VARCHAR(64) NOT NULL,
            pin VARCHAR(64) NOT NULL,
            name VARCHAR(255) NULL,
            privilege VARCHAR(32) NULL,
            password VARCHAR(255) NULL,
            card VARCHAR(64) NULL,
            group_no VARCHAR(32) NULL,
            timezone VARCHAR(255) NULL,
            verify_mode VARCHAR(32) NULL,
            vice_card VARCHAR(64) NULL,
            start_datetime VARCHAR(64) NULL,
            end_datetime VARCHAR(64) NULL,
            raw_request_id INT NOT NULL,
            receive_time DATETIME NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            CONSTRAINT fk_device_user_raw_request_id FOREIGN KEY (raw_request_id) REFERENCES raw_request(id),
            CONSTRAINT uq_device_user_device_pin UNIQUE (device_sn, pin)
        )
        """,
        "CREATE INDEX ix_device_user_device_sn ON device_user (device_sn)",
        "CREATE INDEX ix_device_user_pin ON device_user (pin)",
    )

    with engine.begin() as connection:
        for statement in statements:
            try:
                connection.execute(text(statement))
            except Exception as exc:
                error_text = str(exc).lower()
                if "duplicate key name" in error_text or "already exists" in error_text:
                    continue
                raise
