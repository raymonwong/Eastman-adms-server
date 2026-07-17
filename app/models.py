from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Device(Base):
    __tablename__ = "device"
    __table_args__ = (UniqueConstraint("device_sn", name="uq_device_device_sn"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_sn: Mapped[str] = mapped_column(String(64), nullable=False)
    device_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    record_attendance: Mapped[bool] = mapped_column(Boolean, server_default="1", nullable=False)
    show_in_console: Mapped[bool] = mapped_column(Boolean, server_default="1", nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    firmware_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_online: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_online: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_handshake_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    push_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    language: Mapped[str | None] = mapped_column(String(32), nullable=True)
    push_options: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class RawRequest(Base):
    __tablename__ = "raw_request"
    __table_args__ = (
        Index("ix_raw_request_device_sn", "device_sn"),
        Index("ix_raw_request_received_at", "received_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_sn: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_method: Mapped[str] = mapped_column(String(16), nullable=False)
    request_url: Mapped[str] = mapped_column(Text, nullable=False)
    request_path: Mapped[str] = mapped_column(String(255), nullable=False)
    query_string: Mapped[str | None] = mapped_column(Text, nullable=True)
    query_params: Mapped[str | None] = mapped_column(Text, nullable=True)
    headers: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_body: Mapped[str] = mapped_column(Text, nullable=False)
    response_status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    request_size: Mapped[int] = mapped_column(Integer, nullable=False)
    response_size: Mapped[int] = mapped_column(Integer, nullable=False)
    parsed: Mapped[bool] = mapped_column(Boolean, server_default="0", nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DeviceEventLog(Base):
    __tablename__ = "device_event_log"
    __table_args__ = (
        Index("ix_device_event_log_device_sn", "device_sn"),
        Index("ix_device_event_log_connect_time", "connect_time"),
        Index("ix_device_event_log_request_hash", "request_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    device_sn: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("device.id"), nullable=True)
    client_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    connect_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (
        Index("ix_attendance_device_sn", "device_sn"),
        Index("ix_attendance_employee_code", "employee_code"),
        Index("ix_attendance_attendance_time", "attendance_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_sn: Mapped[str] = mapped_column(String(64), nullable=False)
    employee_code: Mapped[str] = mapped_column(String(64), nullable=False)
    verify_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    attendance_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    work_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_request_id: Mapped[int | None] = mapped_column(ForeignKey("raw_request.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AttendanceEvent(Base):
    __tablename__ = "attendance_event"
    __table_args__ = (
        UniqueConstraint(
            "device_sn",
            "pin",
            "attendance_time",
            "verify",
            name="uq_attendance_event_device_pin_time_verify",
        ),
        Index("ix_attendance_event_device_sn", "device_sn"),
        Index("ix_attendance_event_pin", "pin"),
        Index("ix_attendance_event_attendance_time", "attendance_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_sn: Mapped[str] = mapped_column(String(64), nullable=False)
    pin: Mapped[str] = mapped_column(String(64), nullable=False)
    attendance_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    verify: Mapped[str] = mapped_column(String(32), nullable=False)
    work_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reserved1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reserved2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mask_flag: Mapped[str | None] = mapped_column(String(32), nullable=True)
    temperature: Mapped[str | None] = mapped_column(String(32), nullable=True)
    conv_temperature: Mapped[str | None] = mapped_column(String(32), nullable=True)
    receive_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_request_id: Mapped[int] = mapped_column(ForeignKey("raw_request.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class OperationEvent(Base):
    __tablename__ = "operation_event"
    __table_args__ = (
        Index("ix_operation_event_device_sn", "device_sn"),
        Index("ix_operation_event_operation_code", "operation_code"),
        Index("ix_operation_event_operation_time", "operation_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_sn: Mapped[str] = mapped_column(String(64), nullable=False)
    operation_code: Mapped[str] = mapped_column(String(32), nullable=False)
    operation_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    operator: Mapped[str | None] = mapped_column(String(64), nullable=True)
    operation_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    operation_object: Mapped[str | None] = mapped_column(String(128), nullable=True)
    value1: Mapped[str | None] = mapped_column(Text, nullable=True)
    value2: Mapped[str | None] = mapped_column(Text, nullable=True)
    value3: Mapped[str | None] = mapped_column(Text, nullable=True)
    receive_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_request_id: Mapped[int] = mapped_column(ForeignKey("raw_request.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DeviceSyncState(Base):
    __tablename__ = "device_sync_state"
    __table_args__ = (
        UniqueConstraint("device_sn", "data_type", name="uq_device_sync_state_device_type"),
        Index("ix_device_sync_state_device_sn", "device_sn"),
        Index("ix_device_sync_state_data_type", "data_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_sn: Mapped[str] = mapped_column(String(64), nullable=False)
    data_type: Mapped[str] = mapped_column(String(32), nullable=False)
    device_stamp: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_success_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_raw_request_id: Mapped[int | None] = mapped_column(ForeignKey("raw_request.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class DeviceUser(Base):
    __tablename__ = "device_user"
    __table_args__ = (
        UniqueConstraint("device_sn", "pin", name="uq_device_user_device_pin"),
        UniqueConstraint("employee_id", name="uq_device_user_employee_id"),
        Index("ix_device_user_device_sn", "device_sn"),
        Index("ix_device_user_pin", "pin"),
        Index("ix_device_user_employee_id", "employee_id"),
        Index("ix_device_user_employee_record_id", "employee_record_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_sn: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pin: Mapped[str | None] = mapped_column(String(64), nullable=True)
    employee_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    employee_record_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    privilege: Mapped[str | None] = mapped_column(String(32), nullable=True)
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    card: Mapped[str | None] = mapped_column(String(64), nullable=True)
    card_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, server_default="1", nullable=False)
    group_no: Mapped[str | None] = mapped_column(String(32), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verify_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    vice_card: Mapped[str | None] = mapped_column(String(64), nullable=True)
    start_datetime: Mapped[str | None] = mapped_column(String(64), nullable=True)
    end_datetime: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_request_id: Mapped[int | None] = mapped_column(ForeignKey("raw_request.id"), nullable=True)
    receive_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_device_sn: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_device_user_upload_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_device_raw_request_id: Mapped[int | None] = mapped_column(ForeignKey("raw_request.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class DeviceUserSync(Base):
    __tablename__ = "device_user_sync"
    __table_args__ = (
        UniqueConstraint("employee_id", "device_sn", name="uq_device_user_sync_employee_device"),
        CheckConstraint(
            "sync_status IN ('PENDING','SYNCING','SYNCED','FAILED')",
            name="ck_device_user_sync_status",
        ),
        Index("ix_device_user_sync_employee_id", "employee_id"),
        Index("ix_device_user_sync_device_sn", "device_sn"),
        Index("ix_device_user_sync_status", "sync_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("device_user.employee_id"), nullable=False)
    device_sn: Mapped[str] = mapped_column(ForeignKey("device.device_sn"), nullable=False)
    sync_status: Mapped[str] = mapped_column(String(32), server_default="PENDING", nullable=False)
    last_sync_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SyncLog(Base):
    __tablename__ = "sync_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attendance_id: Mapped[int | None] = mapped_column(ForeignKey("attendance.id"), nullable=True)
    sync_status: Mapped[str] = mapped_column(String(32), nullable=False)
    sync_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sync_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
