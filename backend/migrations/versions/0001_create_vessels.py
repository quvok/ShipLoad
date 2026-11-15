"""Create the vessel registry.

Revision ID: 0001_create_vessels
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_create_vessels"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vessels",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("vessel_type", sa.String(length=40), nullable=False),
        sa.Column("loa_m", sa.Float(), nullable=False),
        sa.Column("lbp_m", sa.Float(), nullable=False),
        sa.Column("moulded_breadth_m", sa.Float(), nullable=False),
        sa.Column("moulded_depth_m", sa.Float(), nullable=False),
        sa.Column("coordinate_convention", sa.JSON(), nullable=False),
        sa.Column("data_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_vessels_name", "vessels", ["name"])


def downgrade() -> None:
    op.drop_index("ix_vessels_name", table_name="vessels")
    op.drop_table("vessels")
