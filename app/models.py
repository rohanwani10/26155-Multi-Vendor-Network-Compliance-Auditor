from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    vendor: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    os_version: Mapped[str | None] = mapped_column(String, nullable=True)
    serial: Mapped[str | None] = mapped_column(String, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    configs: Mapped[list["ParsedConfig"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )


class ParsedConfig(Base):
    __tablename__ = "parsed_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    parse_tier: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    device: Mapped["Device"] = relationship(back_populates="configs")


class PendingReview(Base):
    """A Tier-1-unrecognized config line that Tier-2 (embedding match, then
    local LLM) couldn't confidently classify either. Queued here for a
    human to resolve via the Phase 4 Training UI."""

    __tablename__ = "pending_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    parsed_config_id: Mapped[int] = mapped_column(ForeignKey("parsed_configs.id"), nullable=False)
    vendor: Mapped[str] = mapped_column(String, nullable=False)
    raw_line: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_category: Mapped[str | None] = mapped_column(String, nullable=True)
    suggested_field: Mapped[str | None] = mapped_column(String, nullable=True)
    suggested_value: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class LearnedRule(Base):
    """A human-validated mapping for an unrecognized pattern (vendor + raw_pattern),
    mapping it to a specific category, field, and value."""

    __tablename__ = "learned_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vendor: Mapped[str] = mapped_column(String, nullable=False)
    raw_pattern: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    field: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str | None] = mapped_column(String, nullable=True)
    created_by: Mapped[str] = mapped_column(String, default="admin")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class Finding(Base):
    """An evaluation finding resulting from checking a device's normalized_json
    against a security framework rule pack (CIS, NIST, STIG, ISO)."""

    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    rule_id: Mapped[str] = mapped_column(String, nullable=False)
    framework: Mapped[str] = mapped_column(String, nullable=False, default="CIS")
    title: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    remediation_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    device: Mapped["Device"] = relationship(back_populates="findings")


