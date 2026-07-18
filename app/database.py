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
    # Existing DT008 databases already have device_user but not DT010 columns.
    # Prepare referenced columns before SQLAlchemy creates device_user_sync FKs.
    ensure_dt010_1_user_sync_prerequisites(engine)
    # SQLAlchemy create_all is idempotent and only creates tables that do not exist.
    Base.metadata.create_all(bind=engine)
    ensure_dt003_columns(engine)
    ensure_dt004_columns(engine)
    ensure_dt005_tables(engine)
    ensure_dt006_tables(engine)
    ensure_dt007_tables(engine)
    ensure_dt008_tables(engine)
    ensure_dt009_6_device_management(engine)
    ensure_dt010_1_user_sync(engine)
    ensure_integration_settings(engine)
    ensure_dt012_1_fingerprint_tables(engine)
    ensure_dt014_attendance_mingdao_sync(engine)


def ensure_dt010_1_user_sync_prerequisites(engine: Engine) -> None:
    statements = (
        "ALTER TABLE device_user MODIFY device_sn VARCHAR(64) NULL",
        "ALTER TABLE device_user MODIFY pin VARCHAR(64) NULL",
        "ALTER TABLE device_user MODIFY raw_request_id INT NULL",
        "ALTER TABLE device_user MODIFY receive_time DATETIME NULL",
        "ALTER TABLE device_user ADD COLUMN employee_id VARCHAR(64) NULL",
        "ALTER TABLE device_user ADD COLUMN employee_record_id VARCHAR(128) NULL",
        "ALTER TABLE device_user ADD COLUMN department VARCHAR(255) NULL",
        "ALTER TABLE device_user ADD COLUMN card_no VARCHAR(64) NULL",
        "ALTER TABLE device_user ADD COLUMN enabled BOOL NOT NULL DEFAULT 1",
        "ALTER TABLE device_user ADD COLUMN last_device_sn VARCHAR(64) NULL",
        "ALTER TABLE device_user ADD COLUMN last_device_user_upload_at DATETIME NULL",
        "ALTER TABLE device_user ADD COLUMN last_device_raw_request_id INT NULL",
        "CREATE UNIQUE INDEX uq_device_user_employee_id ON device_user (employee_id)",
        "CREATE INDEX ix_device_user_employee_id ON device_user (employee_id)",
        "CREATE INDEX ix_device_user_employee_record_id ON device_user (employee_record_id)",
    )

    with engine.begin() as connection:
        for statement in statements:
            try:
                connection.execute(text(statement))
            except Exception as exc:
                error_text = str(exc).lower()
                if (
                    "doesn't exist" in error_text
                    or "unknown table" in error_text
                    or "duplicate column" in error_text
                    or "duplicate key name" in error_text
                    or "already exists" in error_text
                ):
                    continue
                raise


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


def ensure_dt009_6_device_management(engine: Engine) -> None:
    # DT009.6 adds device configuration fields to the existing device table.
    statements = (
        "ALTER TABLE device ADD COLUMN location VARCHAR(255) NULL",
        "ALTER TABLE device ADD COLUMN record_attendance BOOL NOT NULL DEFAULT 1",
        "ALTER TABLE device ADD COLUMN show_in_console BOOL NOT NULL DEFAULT 1",
        "UPDATE device SET device_name = 'New Machine' WHERE device_name IS NULL OR device_name = ''",
    )

    with engine.begin() as connection:
        for statement in statements:
            try:
                connection.execute(text(statement))
            except Exception as exc:
                if "duplicate column" in str(exc).lower():
                    continue
                raise


def ensure_dt010_1_user_sync(engine: Engine) -> None:
    # DT010.1 extends device_user for Mingdao-sourced users and adds per-device sync state.
    statements = (
        "ALTER TABLE device_user MODIFY device_sn VARCHAR(64) NULL",
        "ALTER TABLE device_user MODIFY pin VARCHAR(64) NULL",
        "ALTER TABLE device_user MODIFY raw_request_id INT NULL",
        "ALTER TABLE device_user MODIFY receive_time DATETIME NULL",
        "ALTER TABLE device_user ADD COLUMN employee_id VARCHAR(64) NULL",
        "ALTER TABLE device_user ADD COLUMN employee_record_id VARCHAR(128) NULL",
        "ALTER TABLE device_user ADD COLUMN department VARCHAR(255) NULL",
        "ALTER TABLE device_user ADD COLUMN card_no VARCHAR(64) NULL",
        "ALTER TABLE device_user ADD COLUMN enabled BOOL NOT NULL DEFAULT 1",
        "ALTER TABLE device_user ADD COLUMN last_device_sn VARCHAR(64) NULL",
        "ALTER TABLE device_user ADD COLUMN last_device_user_upload_at DATETIME NULL",
        "ALTER TABLE device_user ADD COLUMN last_device_raw_request_id INT NULL",
        "CREATE UNIQUE INDEX uq_device_user_employee_id ON device_user (employee_id)",
        "CREATE INDEX ix_device_user_employee_id ON device_user (employee_id)",
        "CREATE INDEX ix_device_user_employee_record_id ON device_user (employee_record_id)",
        """
        CREATE TABLE IF NOT EXISTS device_user_sync (
            id INT NOT NULL AUTO_INCREMENT,
            employee_id VARCHAR(64) NOT NULL,
            device_sn VARCHAR(64) NOT NULL,
            sync_status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
            last_sync_time DATETIME NULL,
            retry_count INT NOT NULL DEFAULT 0,
            last_error TEXT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            CONSTRAINT uq_device_user_sync_employee_device UNIQUE (employee_id, device_sn),
            CONSTRAINT ck_device_user_sync_status CHECK (sync_status IN ('PENDING','SYNCING','SYNCED','FAILED')),
            CONSTRAINT fk_device_user_sync_employee_id FOREIGN KEY (employee_id) REFERENCES device_user(employee_id),
            CONSTRAINT fk_device_user_sync_device_sn FOREIGN KEY (device_sn) REFERENCES device(device_sn)
        )
        """,
        "CREATE INDEX ix_device_user_sync_employee_id ON device_user_sync (employee_id)",
        "CREATE INDEX ix_device_user_sync_device_sn ON device_user_sync (device_sn)",
        "CREATE INDEX ix_device_user_sync_status ON device_user_sync (sync_status)",
        """
        DELETE dus FROM device_user_sync dus
        LEFT JOIN device_user du ON du.employee_id = dus.employee_id
        WHERE du.employee_id IS NULL
        """,
        """
        DELETE dus FROM device_user_sync dus
        LEFT JOIN device d ON d.device_sn = dus.device_sn
        WHERE d.device_sn IS NULL
        """,
        "ALTER TABLE device_user_sync ADD CONSTRAINT ck_device_user_sync_status CHECK (sync_status IN ('PENDING','SYNCING','SYNCED','FAILED'))",
        "ALTER TABLE device_user_sync ADD CONSTRAINT fk_device_user_sync_employee_id FOREIGN KEY (employee_id) REFERENCES device_user(employee_id)",
        "ALTER TABLE device_user_sync ADD CONSTRAINT fk_device_user_sync_device_sn FOREIGN KEY (device_sn) REFERENCES device(device_sn)",
        "ALTER TABLE device_user ADD CONSTRAINT fk_device_user_last_device_raw_request_id FOREIGN KEY (last_device_raw_request_id) REFERENCES raw_request(id)",
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
                    or "duplicate check constraint name" in error_text
                    or "already exists" in error_text
                    or "duplicate foreign key constraint name" in error_text
                ):
                    continue
                raise


def ensure_dt014_attendance_mingdao_sync(engine: Engine) -> None:
    # DT014 records every Mingdao attendance write attempt by attendance_event.id.
    # The unique constraint is the local idempotency key that prevents duplicate uploads.
    statements = (
        """
        CREATE TABLE IF NOT EXISTS attendance_mingdao_sync (
            id INT NOT NULL AUTO_INCREMENT,
            attendance_event_id INT NOT NULL,
            sync_status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
            mingdao_row_id VARCHAR(128) NULL,
            last_sync_time DATETIME NULL,
            retry_count INT NOT NULL DEFAULT 0,
            last_error TEXT NULL,
            request_payload TEXT NULL,
            response_body TEXT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            CONSTRAINT uq_attendance_mingdao_sync_event UNIQUE (attendance_event_id),
            CONSTRAINT ck_attendance_mingdao_sync_status CHECK (sync_status IN ('PENDING','SYNCING','SYNCED','FAILED')),
            CONSTRAINT fk_attendance_mingdao_sync_event FOREIGN KEY (attendance_event_id) REFERENCES attendance_event(id)
        )
        """,
        "CREATE INDEX ix_attendance_mingdao_sync_event_id ON attendance_mingdao_sync (attendance_event_id)",
        "CREATE INDEX ix_attendance_mingdao_sync_status ON attendance_mingdao_sync (sync_status)",
        "CREATE INDEX ix_attendance_mingdao_sync_last_sync_time ON attendance_mingdao_sync (last_sync_time)",
        "ALTER TABLE attendance_mingdao_sync ADD CONSTRAINT ck_attendance_mingdao_sync_status CHECK (sync_status IN ('PENDING','SYNCING','SYNCED','FAILED'))",
        "ALTER TABLE attendance_mingdao_sync ADD CONSTRAINT fk_attendance_mingdao_sync_event FOREIGN KEY (attendance_event_id) REFERENCES attendance_event(id)",
    )

    with engine.begin() as connection:
        for statement in statements:
            try:
                connection.execute(text(statement))
            except Exception as exc:
                error_text = str(exc).lower()
                if (
                    "duplicate key name" in error_text
                    or "duplicate check constraint name" in error_text
                    or "already exists" in error_text
                    or "duplicate foreign key constraint name" in error_text
                ):
                    continue
                raise


def ensure_dt012_1_fingerprint_tables(engine: Engine) -> None:
    # DT012.1 stores FP records uploaded by real devices inside OPERLOG bodies.
    # Distribution to other devices is intentionally out of scope for this stage.
    statements = (
        """
        CREATE TABLE IF NOT EXISTS device_user_fingerprint (
            id INT NOT NULL AUTO_INCREMENT,
            device_sn VARCHAR(64) NOT NULL,
            pin VARCHAR(64) NOT NULL,
            finger_id VARCHAR(32) NOT NULL,
            template_size INT NULL,
            valid VARCHAR(16) NULL,
            template_data TEXT NOT NULL,
            template_hash VARCHAR(64) NOT NULL,
            source_device_sn VARCHAR(64) NOT NULL,
            raw_request_id INT NULL,
            receive_time DATETIME NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            CONSTRAINT uq_device_user_fingerprint_pin_finger UNIQUE (pin, finger_id),
            CONSTRAINT fk_device_user_fingerprint_raw_request_id FOREIGN KEY (raw_request_id) REFERENCES raw_request(id)
        )
        """,
        "CREATE INDEX ix_device_user_fingerprint_device_sn ON device_user_fingerprint (device_sn)",
        "CREATE INDEX ix_device_user_fingerprint_pin ON device_user_fingerprint (pin)",
        "CREATE INDEX ix_device_user_fingerprint_source_device_sn ON device_user_fingerprint (source_device_sn)",
        "CREATE INDEX ix_device_user_fingerprint_template_hash ON device_user_fingerprint (template_hash)",
        "ALTER TABLE device_user_fingerprint ADD CONSTRAINT fk_device_user_fingerprint_raw_request_id FOREIGN KEY (raw_request_id) REFERENCES raw_request(id)",
    )

    with engine.begin() as connection:
        for statement in statements:
            try:
                connection.execute(text(statement))
            except Exception as exc:
                error_text = str(exc).lower()
                if (
                    "duplicate key name" in error_text
                    or "already exists" in error_text
                    or "duplicate foreign key constraint name" in error_text
                ):
                    continue
                raise


def ensure_integration_settings(engine: Engine) -> None:
    # Persistent console configuration. Environment variables remain defaults,
    # but UI changes must survive page refreshes and container restarts.
    statements = (
        """
        CREATE TABLE IF NOT EXISTS integration_setting (
            setting_key VARCHAR(128) NOT NULL,
            setting_value TEXT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (setting_key)
        )
        """,
    )

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
