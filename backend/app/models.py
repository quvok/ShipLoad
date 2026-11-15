"""SQLAlchemy persistence models."""
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class VesselRecord(Base):
    __tablename__ = "vessels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    vessel_type: Mapped[str] = mapped_column(String(40), nullable=False)
    loa_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    lbp_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    moulded_breadth_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    moulded_depth_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    coordinate_convention: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    data_status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(UTC),
    )
    loading_conditions: Mapped[list["LoadingConditionRecord"]] = relationship(
        back_populates="vessel", cascade="all, delete-orphan"
    )
    tanks: Mapped[list["TankRecord"]] = relationship(back_populates="vessel")


class TankRecord(Base):
    __tablename__ = "tanks"
    __table_args__ = (
        UniqueConstraint("vessel_id", "tank_code", name="uq_tank_code_per_vessel"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    vessel_id: Mapped[str] = mapped_column(
        ForeignKey("vessels.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    tank_code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    tank_type: Mapped[str] = mapped_column(String(40), nullable=False)
    nominal_capacity_m3: Mapped[float | None] = mapped_column(Float, nullable=True)
    arrangement_source_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    capacity_source_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    data_status: Mapped[str] = mapped_column(String(32), nullable=False, default="REVIEW_REQUIRED")
    vessel: Mapped[VesselRecord] = relationship(back_populates="tanks")


class LoadingConditionRecord(Base):
    __tablename__ = "loading_conditions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    vessel_id: Mapped[str] = mapped_column(
        ForeignKey("vessels.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    vessel_data_revision: Mapped[str] = mapped_column(String(80), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="REVIEW_REQUIRED")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(UTC),
    )
    vessel: Mapped[VesselRecord] = relationship(back_populates="loading_conditions")
    items: Mapped[list["LoadingItemRecord"]] = relationship(
        back_populates="condition", cascade="all, delete-orphan",
        order_by="LoadingItemRecord.item_id",
    )


class LoadingItemRecord(Base):
    __tablename__ = "loading_items"
    __table_args__ = (
        UniqueConstraint("condition_id", "item_id", name="uq_loading_item_per_condition"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    condition_id: Mapped[str] = mapped_column(
        ForeignKey("loading_conditions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(String(240), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    mass_kg: Mapped[float] = mapped_column(Float, nullable=False)
    position: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tank_id: Mapped[str | None] = mapped_column(ForeignKey("tanks.id", ondelete="RESTRICT"), nullable=True)
    source_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    condition: Mapped[LoadingConditionRecord] = relationship(back_populates="items")


class SourceDocumentRecord(Base):
    __tablename__ = "source_documents"
    __table_args__ = (
        UniqueConstraint("vessel_id", "sha256", name="uq_source_document_hash_per_vessel"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    vessel_id: Mapped[str] = mapped_column(
        ForeignKey("vessels.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    document_type: Mapped[str] = mapped_column(String(40), nullable=False, default="other")
    extraction_status: Mapped[str] = mapped_column(String(40), nullable=False)
    extracted_candidates: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    analysis_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extraction_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    analysis_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    vessel: Mapped[VesselRecord] = relationship()


class VesselDataRevisionRecord(Base):
    """Immutable, reviewed snapshot of vessel particulars and their provenance."""

    __tablename__ = "vessel_data_revisions"
    __table_args__ = (
        UniqueConstraint("vessel_id", "revision_number", name="uq_vessel_data_revision_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    vessel_id: Mapped[str] = mapped_column(
        ForeignKey("vessels.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    values: Mapped[dict] = mapped_column(JSON, nullable=False)
    source_references: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_by: Mapped[str] = mapped_column(String(80), nullable=False)
    change_summary: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class DocumentCandidateDecisionRecord(Base):
    """Append-only decision record for one extracted candidate."""

    __tablename__ = "document_candidate_decisions"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "candidate_index", name="uq_document_candidate_decision"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(
        ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    candidate_index: Mapped[int] = mapped_column(Integer, nullable=False)
    field: Mapped[str] = mapped_column(String(80), nullable=False)
    proposed_value: Mapped[float] = mapped_column(Float, nullable=False)
    approved_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    matched_text: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    revision_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewer_label: Mapped[str] = mapped_column(String(80), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
