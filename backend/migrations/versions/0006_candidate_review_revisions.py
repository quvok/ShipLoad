"""Add immutable vessel-data revisions and candidate review audit.

Revision ID: 0006_candidate_review_revisions
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_candidate_review_revisions"
down_revision = "0005_document_first_vessel_drafts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vessel_data_revisions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("vessel_id", sa.String(length=36), sa.ForeignKey("vessels.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("values", sa.JSON(), nullable=False),
        sa.Column("source_references", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=80), nullable=False),
        sa.Column("change_summary", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("vessel_id", "revision_number", name="uq_vessel_data_revision_number"),
    )
    op.create_index("ix_vessel_data_revisions_vessel_id", "vessel_data_revisions", ["vessel_id"])
    op.create_table(
        "document_candidate_decisions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_id", sa.String(length=36), sa.ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("candidate_index", sa.Integer(), nullable=False),
        sa.Column("field", sa.String(length=80), nullable=False),
        sa.Column("proposed_value", sa.Float(), nullable=False),
        sa.Column("approved_value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("matched_text", sa.Text(), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("reviewer_label", sa.String(length=80), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("document_id", "candidate_index", name="uq_document_candidate_decision"),
    )
    op.create_index("ix_document_candidate_decisions_document_id", "document_candidate_decisions", ["document_id"])


def downgrade() -> None:
    raise RuntimeError(
        "Candidate decisions and approved vessel-data revisions are audit records and must not be deleted."
    )
