"""Add immutable source document registry.

Revision ID: 0004_source_documents
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_source_documents"
down_revision = "0003_tank_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("vessel_id", sa.String(length=36), sa.ForeignKey("vessels.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=80), nullable=False, unique=True),
        sa.Column("media_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("document_type", sa.String(length=40), nullable=False),
        sa.Column("extraction_status", sa.String(length=40), nullable=False),
        sa.Column("extracted_candidates", sa.JSON(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("vessel_id", "sha256", name="uq_source_document_hash_per_vessel"),
    )
    op.create_index("ix_source_documents_vessel_id", "source_documents", ["vessel_id"])


def downgrade() -> None:
    op.drop_index("ix_source_documents_vessel_id", table_name="source_documents")
    op.drop_table("source_documents")
