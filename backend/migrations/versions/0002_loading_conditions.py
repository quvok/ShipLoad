"""Add persistent loading conditions and their items.

Revision ID: 0002_loading_conditions
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_loading_conditions"
down_revision = "0001_create_vessels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "loading_conditions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "vessel_id",
            sa.String(length=36),
            sa.ForeignKey("vessels.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("vessel_data_revision", sa.String(length=80), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_loading_conditions_vessel_id", "loading_conditions", ["vessel_id"]
    )
    op.create_table(
        "loading_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "condition_id",
            sa.String(length=36),
            sa.ForeignKey("loading_conditions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_id", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=240), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("mass_kg", sa.Float(), nullable=False),
        sa.Column("position", sa.JSON(), nullable=True),
        sa.Column("tank_id", sa.String(length=80), nullable=True),
        sa.Column("source_reference", sa.String(length=500), nullable=False),
        sa.UniqueConstraint(
            "condition_id", "item_id", name="uq_loading_item_per_condition"
        ),
    )
    op.create_index("ix_loading_items_condition_id", "loading_items", ["condition_id"])


def downgrade() -> None:
    op.drop_index("ix_loading_items_condition_id", table_name="loading_items")
    op.drop_table("loading_items")
    op.drop_index("ix_loading_conditions_vessel_id", table_name="loading_conditions")
    op.drop_table("loading_conditions")
