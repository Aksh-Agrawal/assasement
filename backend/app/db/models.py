"""Relational attempt storage with portable SQLAlchemy types."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PairingSession(Base):
    __tablename__ = "pairing_sessions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"))
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    claim_secret_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    device: Mapped[Device] = relationship()


class DeviceCredential(Base):
    __tablename__ = "device_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"))
    credential_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    secret_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    device: Mapped[Device] = relationship()


class QuestionPack(Base):
    __tablename__ = "question_packs"
    __table_args__ = (
        UniqueConstraint("set_id", "version", name="uq_question_packs_set_version"),
        Index("ix_question_packs_catalog", "subject", "set_id", "version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    set_id: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str] = mapped_column(String(64), nullable=False)
    chapter: Mapped[str] = mapped_column(String(200), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Attempt(Base):
    __tablename__ = "attempts"
    __table_args__ = (
        UniqueConstraint("device_attempt_id", name="uq_attempts_device_attempt_id"),
        Index("ix_attempts_profile_id", "profile_id"),
        Index(
            "ix_attempts_question_set_id_version", "question_set_id", "question_set_version"
        ),
        Index("ix_attempts_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    authenticated_device_id: Mapped[int | None] = mapped_column(
        ForeignKey("devices.id", ondelete="RESTRICT")
    )
    device_attempt_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    payload_version: Mapped[int] = mapped_column(Integer, nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(255))
    profile_id: Mapped[str] = mapped_column(String(255), nullable=False)
    server_user_id: Mapped[str | None] = mapped_column(String(255))
    question_set_id: Mapped[str] = mapped_column(String(255), nullable=False)
    question_set_version: Mapped[int] = mapped_column(Integer, nullable=False)
    marking_correct: Mapped[float] = mapped_column(Float, nullable=False)
    marking_wrong: Mapped[float] = mapped_column(Float, nullable=False)
    marking_skip: Mapped[float] = mapped_column(Float, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    responses: Mapped[list["AttemptResponse"]] = relationship(
        back_populates="attempt", cascade="save-update, merge"
    )
    authenticated_device: Mapped[Device | None] = relationship()


class AttemptResponse(Base):
    __tablename__ = "attempt_responses"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_attempt_responses_attempt_question"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("attempts.id", ondelete="RESTRICT"), nullable=False
    )
    device_response_id: Mapped[str] = mapped_column(String(255), nullable=False)
    question_id: Mapped[str] = mapped_column(String(255), nullable=False)
    selected_key: Mapped[str | None] = mapped_column(String(1))
    confidence: Mapped[str | None] = mapped_column(String(16))
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    marked_review: Mapped[bool] = mapped_column(Boolean, nullable=False)
    first_shown_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    attempt: Mapped[Attempt] = relationship(back_populates="responses")
