"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-18

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "system_rate_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "base_rate",
            sa.Numeric(10, 6),
            nullable=False,
        ),
        sa.CheckConstraint("base_rate > 0", name="ck_system_rate_configs_base_rate_positive"),
    )

    op.create_table(
        "credit_tier_configs",
        sa.Column("tier", sa.String(1), primary_key=True),
        sa.Column("multiplier", sa.Numeric(10, 6), nullable=False),
        sa.CheckConstraint("tier IN ('A', 'B', 'C')", name="ck_credit_tier_configs_tier_valid"),
        sa.CheckConstraint(
            "multiplier > 0", name="ck_credit_tier_configs_multiplier_positive"
        ),
    )

    op.create_table(
        "district_risk_configs",
        sa.Column("district", sa.Text, primary_key=True),
        sa.Column("multiplier", sa.Numeric(10, 6), nullable=False),
        sa.Column("region2", sa.Text, nullable=False),
        sa.CheckConstraint(
            "multiplier > 0", name="ck_district_risk_configs_multiplier_positive"
        ),
    )
    op.create_index(
        "idx_district_risk_configs_region2", "district_risk_configs", ["region2"]
    )

    op.create_table(
        "postal_code_mappings",
        sa.Column("postal_code", sa.String(5), primary_key=True),
        sa.Column("district", sa.Text, nullable=False),
        sa.Column("region1", sa.Text, nullable=False),
        sa.Column("region2", sa.Text, nullable=False),
        sa.Column("region3", sa.Text, nullable=False),
    )

    op.create_table(
        "outbox",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("correlation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("correlation_id", name="uq_outbox_correlation_id"),
    )
    op.create_index("idx_outbox_created_at", "outbox", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_outbox_created_at", table_name="outbox")
    op.drop_table("outbox")
    op.drop_table("postal_code_mappings")
    op.drop_index("idx_district_risk_configs_region2", table_name="district_risk_configs")
    op.drop_table("district_risk_configs")
    op.drop_table("credit_tier_configs")
    op.drop_table("system_rate_configs")
