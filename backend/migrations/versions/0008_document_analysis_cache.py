"""Cache versioned extraction reports derived from immutable PDFs.

Revision ID: 0008_document_analysis_cache
"""
import sqlalchemy as sa
from alembic import op

revision = "0008_document_analysis_cache"
down_revision = "0007_candidate_decision_revision"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("source_documents", sa.Column("analysis_version", sa.Integer(), nullable=True))
    op.add_column("source_documents", sa.Column("extraction_report", sa.JSON(), nullable=True))
    op.add_column(
        "source_documents",
        sa.Column("analysis_completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("source_documents", "analysis_completed_at")
    op.drop_column("source_documents", "extraction_report")
    op.drop_column("source_documents", "analysis_version")
