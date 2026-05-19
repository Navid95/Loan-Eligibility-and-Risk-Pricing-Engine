import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CalculationRecordModel(Base):
    __tablename__ = "calculation_records"
    __table_args__ = (
        UniqueConstraint(
            "correlation_id", name="uq_calculation_records_correlation_id"
        ),
        Index("idx_calculation_records_calculated_at", "calculated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    correlation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    credit_tier: Mapped[str] = mapped_column(String(1), nullable=False)
    district: Mapped[str] = mapped_column(Text, nullable=False)
    base_rate: Mapped[float] = mapped_column(Numeric(20, 6), nullable=False)
    term_multiplier: Mapped[float] = mapped_column(Numeric(20, 6), nullable=False)
    credit_tier_multiplier: Mapped[float] = mapped_column(
        Numeric(20, 6), nullable=False
    )
    regional_risk_multiplier: Mapped[float] = mapped_column(
        Numeric(20, 6), nullable=False
    )
    final_rate: Mapped[float] = mapped_column(Numeric(20, 6), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
