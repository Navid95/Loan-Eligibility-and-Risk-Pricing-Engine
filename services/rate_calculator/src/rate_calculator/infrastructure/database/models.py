import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SystemRateConfigModel(Base):
    __tablename__ = "system_rate_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    base_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)


class CreditTierConfigModel(Base):
    __tablename__ = "credit_tier_configs"

    tier: Mapped[str] = mapped_column(String(1), primary_key=True)
    multiplier: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)


class DistrictRiskConfigModel(Base):
    __tablename__ = "district_risk_configs"

    district: Mapped[str] = mapped_column(Text, primary_key=True)
    multiplier: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    region2: Mapped[str] = mapped_column(Text, nullable=False, index=True)


class PostalCodeMappingModel(Base):
    __tablename__ = "postal_code_mappings"

    postal_code: Mapped[str] = mapped_column(String(5), primary_key=True)
    district: Mapped[str] = mapped_column(Text, nullable=False)
    region1: Mapped[str] = mapped_column(Text, nullable=False)
    region2: Mapped[str] = mapped_column(Text, nullable=False)
    region3: Mapped[str] = mapped_column(Text, nullable=False)


class OutboxModel(Base):
    __tablename__ = "outbox"
    __table_args__ = (
        UniqueConstraint("correlation_id", name="uq_outbox_correlation_id"),
        Index("idx_outbox_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    correlation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)  # type: ignore[type-arg]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
