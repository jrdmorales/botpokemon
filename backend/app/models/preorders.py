import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class PreorderConfidence(enum.StrEnum):
    HIGH = "alta"  # detección estructurada (tag/categoría de la tienda)
    LOW = "baja"  # detección por keywords — requiere revisión antes de alertar


class PreorderStatus(enum.StrEnum):
    ACTIVE = "activa"
    RELEASED = "lanzada"  # transicionó a stock regular
    PENDING_REVIEW = "pendiente_revision"
    REJECTED = "rechazada"


class Preorder(Base):
    __tablename__ = "preorders"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), unique=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    release_date: Mapped[date | None] = mapped_column(Date)
    payment_terms: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[PreorderConfidence] = mapped_column(Enum(PreorderConfidence, native_enum=False))
    status: Mapped[PreorderStatus] = mapped_column(
        Enum(PreorderStatus, native_enum=False), default=PreorderStatus.ACTIVE
    )
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    listing = relationship("Listing")
