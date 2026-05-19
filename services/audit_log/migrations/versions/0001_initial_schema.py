"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "calculation_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("correlation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("credit_tier", sa.String(1), nullable=False),
        sa.Column("district", sa.Text, nullable=False),
        sa.Column("base_rate", sa.Numeric(20, 6), nullable=False),
        sa.Column("term_multiplier", sa.Numeric(20, 6), nullable=False),
        sa.Column("credit_tier_multiplier", sa.Numeric(20, 6), nullable=False),
        sa.Column("regional_risk_multiplier", sa.Numeric(20, 6), nullable=False),
        sa.Column("final_rate", sa.Numeric(20, 6), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "credit_tier IN ('A', 'B', 'C')",
            name="ck_calculation_records_credit_tier_valid",
        ),
        sa.CheckConstraint(
            "base_rate > 0", name="ck_calculation_records_base_rate_positive"
        ),
        sa.CheckConstraint(
            "final_rate > 0", name="ck_calculation_records_final_rate_positive"
        ),
        sa.UniqueConstraint(
            "correlation_id", name="uq_calculation_records_correlation_id"
        ),
    )
    op.create_index(
        "idx_calculation_records_calculated_at",
        "calculation_records",
        ["calculated_at"],
    )


def downgrade() -> None:
    pass
