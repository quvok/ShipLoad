"""Add vessel tank registry and bind liquid loading items to tanks.

Revision ID: 0003_tank_registry
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_tank_registry"
down_revision = "0002_loading_conditions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tanks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "vessel_id",
            sa.String(length=36),
            sa.ForeignKey("vessels.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("tank_code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("tank_type", sa.String(length=40), nullable=False),
        sa.Column("nominal_capacity_m3", sa.Float(), nullable=True),
        sa.Column("arrangement_source_reference", sa.String(length=500), nullable=False),
        sa.Column("capacity_source_reference", sa.String(length=500), nullable=True),
        sa.Column("data_status", sa.String(length=32), nullable=False),
        sa.UniqueConstraint("vessel_id", "tank_code", name="uq_tank_code_per_vessel"),
    )
    op.create_index("ix_tanks_vessel_id", "tanks", ["vessel_id"])
    with op.batch_alter_table("loading_items") as batch_op:
        batch_op.create_foreign_key(
            "fk_loading_items_tank_id_tanks",
            "tanks",
            ["tank_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table("loading_items") as batch_op:
        batch_op.drop_constraint("fk_loading_items_tank_id_tanks", type_="foreignkey")
    op.drop_index("ix_tanks_vessel_id", table_name="tanks")
    op.drop_table("tanks")
