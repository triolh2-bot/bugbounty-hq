from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash


class Base(DeclarativeBase):
    pass


def _format_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%d %H:%M:%S")


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    scope: Mapped[str | None] = mapped_column(Text)
    rules: Mapped[str | None] = mapped_column(Text)
    bounty_range: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", server_default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    submissions: Mapped[list[Submission]] = relationship(
        back_populates="program", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict[str, object | None]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "scope": self.scope,
            "rules": self.rules,
            "bounty_range": self.bounty_range,
            "status": self.status,
            "created_at": _format_timestamp(self.created_at),
        }


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    program_id: Mapped[str | None] = mapped_column(
        ForeignKey("programs.id"), nullable=True, index=True
    )
    researcher: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str | None] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="submitted", server_default="submitted"
    )
    bounty: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp(), index=True
    )

    program: Mapped[Program | None] = relationship(back_populates="submissions")

    @property
    def program_name(self) -> str | None:
        return self.program.name if self.program else None

    def to_dict(self) -> dict[str, object | None]:
        return {
            "id": self.id,
            "program_id": self.program_id,
            "program_name": self.program_name,
            "researcher": self.researcher,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "status": self.status,
            "bounty": self.bounty,
            "created_at": _format_timestamp(self.created_at),
        }


class IntegrationEvent(Base):
    __tablename__ = "integration_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    external_event_id: Mapped[str | None] = mapped_column(String(255), index=True)
    dedupe_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    event_type: Mapped[str | None] = mapped_column(String(128), index=True)
    signature: Mapped[str | None] = mapped_column(String(255))
    timestamp_header: Mapped[str | None] = mapped_column(String(64))
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    raw_body: Mapped[str] = mapped_column(Text, nullable=False)
    headers_json: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="accepted", server_default="accepted"
    )
    failure_reason: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp(), index=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)
    dead_lettered_at: Mapped[datetime | None] = mapped_column(DateTime)

    def to_dict(self) -> dict[str, object | None]:
        return {
            "id": self.id,
            "provider": self.provider,
            "external_event_id": self.external_event_id,
            "dedupe_key": self.dedupe_key,
            "event_type": self.event_type,
            "signature": self.signature,
            "timestamp_header": self.timestamp_header,
            "payload_hash": self.payload_hash,
            "status": self.status,
            "failure_reason": self.failure_reason,
            "received_at": _format_timestamp(self.received_at),
            "processed_at": _format_timestamp(self.processed_at),
            "dead_lettered_at": _format_timestamp(self.dead_lettered_at),
        }


class Researcher(Base):
    __tablename__ = "researchers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    reputation: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", index=True
    )
    bugs_found: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    total_earnings: Mapped[float] = mapped_column(
        Float, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    def to_dict(self) -> dict[str, object | None]:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "reputation": self.reputation,
            "bugs_found": self.bugs_found,
            "total_earnings": self.total_earnings,
            "created_at": _format_timestamp(self.created_at),
        }


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(32), nullable=False, default="researcher", server_default="researcher"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict[str, object | None]:
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": _format_timestamp(self.created_at),
        }
