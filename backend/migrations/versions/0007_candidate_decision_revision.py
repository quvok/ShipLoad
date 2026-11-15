"""Store the exact vessel revision created by each candidate approval.

Revision ID: 0007_candidate_decision_revision
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_candidate_decision_revision"
down_revision = "0006_candidate_review_revisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document_candidate_decisions",
        sa.Column("revision_number", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    raise RuntimeError(
        "Candidate decision revision references are audit data and must not be removed."
    )
