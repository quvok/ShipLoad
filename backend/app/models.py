"""SQLAlchemy persistence models."""
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class VesselRecord(Base):
    __tablename__ = "vessels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    vessel_type: Mapped[str] = mapped_column(String(40), nullable=False)
    loa_m: Mapped[float] = mapped_column(Float, nullable=False)
    lbp_m: Mapped[float] = mapped_column(Float, nullable=False)
    moulded_breadth_m: Mapped[float] = mapped_column(Float, nullable=False)
    moulded_depth_m: Mapped[float] = mapped_column(Float, nullable=False)
    coordinate_convention: Mapped[dict] = mapped_column(JSON, nullable=False)
    data_status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(UTC),
    )
    loading_conditions: Mapped[list["LoadingConditionRecord"]] = relationship(
        back_populates="vessel", cascade="all, delete-orphan"
    )


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
        default=lambda: datetime.now(timezone.utc),
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
    tank_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    condition: Mapped[LoadingConditionRecord] = relationship(back_populates="items")
