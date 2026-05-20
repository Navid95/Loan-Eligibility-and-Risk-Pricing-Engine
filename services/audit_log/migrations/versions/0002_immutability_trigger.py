"""immutability trigger for calculation_records

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-19

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION raise_on_calculation_record_modification()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION
                'calculation_records is append-only: UPDATE is not permitted';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER tg_calculation_records_immutable
            BEFORE UPDATE ON calculation_records
            FOR EACH STATEMENT
            EXECUTE FUNCTION raise_on_calculation_record_modification()
        """
    )


def downgrade() -> None:
    pass
