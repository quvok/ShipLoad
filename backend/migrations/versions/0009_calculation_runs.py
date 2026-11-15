"""Persist immutable preliminary loading calculation snapshots."""
import sqlalchemy as sa
from alembic import op

revision = "0009_calculation_runs"
down_revision = "0008_document_analysis_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "calculation_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("vessel_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("vessel_data_revision", sa.String(length=80), nullable=False),
        sa.Column("engine_version", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("calculation_input", sa.JSON(), nullable=False),
        sa.Column("calculation_result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["vessel_id"], ["vessels.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_calculation_runs_vessel_id", "calculation_runs", ["vessel_id"])


def downgrade() -> None:
    op.drop_index("ix_calculation_runs_vessel_id", table_name="calculation_runs")
    op.drop_table("calculation_runs")
