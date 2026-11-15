"""Allow document-first vessel drafts without invented particulars.

Revision ID: 0005_document_first_vessel_drafts
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_document_first_vessel_drafts"
down_revision = "0004_source_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("vessels") as batch_op:
        batch_op.alter_column("loa_m", existing_type=sa.Float(), nullable=True)
        batch_op.alter_column("lbp_m", existing_type=sa.Float(), nullable=True)
        batch_op.alter_column("moulded_breadth_m", existing_type=sa.Float(), nullable=True)
        batch_op.alter_column("moulded_depth_m", existing_type=sa.Float(), nullable=True)
        batch_op.alter_column("coordinate_convention", existing_type=sa.JSON(), nullable=True)


def downgrade() -> None:
    raise RuntimeError(
        "Cannot safely restore NOT NULL constraints: document-first draft records may omit particulars."
    )
