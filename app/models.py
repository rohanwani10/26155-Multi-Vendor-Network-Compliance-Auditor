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
