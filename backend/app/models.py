"""SQLAlchemy persistence models."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Float, JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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
        default=lambda: datetime.now(timezone.utc),
    )
