from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.catalog import ListingStatus


class PriceHistory(Base):
    """Serie histórica de precios. Solo inserciones, nunca updates ni deletes.

    Se inserta cuando cambia precio o disponibilidad, más un checkpoint diario
    aunque no haya cambios. En producción, particionar por rango de recorded_at.
    """

    __tablename__ = "price_history"
    __table_args__ = (Index("ix_price_history_listing_ts", "listing_id", "recorded_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"))
    price: Mapped[int] = mapped_column(Integer)
    sale_price: Mapped[int | None] = mapped_column(Integer)
    availability: Mapped[ListingStatus] = mapped_column(String(20))
    is_checkpoint: Mapped[bool] = mapped_column(default=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
