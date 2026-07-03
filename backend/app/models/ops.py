import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ScraperRun(Base):
    __tablename__ = "scraper_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    products_found: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[str | None] = mapped_column(Text)
    success: Mapped[bool] = mapped_column(default=False)


class AlertType(enum.StrEnum):
    NEW_PREORDER = "nueva_preventa"
    DEAL = "oferta"
    HISTORIC_MIN = "minimo_historico"


class AlertSent(Base):
    """Deduplicación de alertas: no re-enviar el mismo evento.

    Se re-alerta solo si el precio bajó respecto a trigger_price.
    """

    __tablename__ = "alerts_sent"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_type: Mapped[AlertType] = mapped_column(Enum(AlertType, native_enum=False), index=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), index=True)
    trigger_price: Mapped[int | None] = mapped_column(Integer)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MatchReviewStatus(enum.StrEnum):
    PENDING = "pendiente"
    APPROVED = "aprobado"
    REJECTED = "rechazado"


class MatchReview(Base):
    __tablename__ = "match_review_queue"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"))
    candidate_product_id: Mapped[int] = mapped_column(ForeignKey("canonical_products.id"))
    score: Mapped[int] = mapped_column(Integer)
    status: Mapped[MatchReviewStatus] = mapped_column(
        Enum(MatchReviewStatus, native_enum=False), default=MatchReviewStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TelegramUser(Base):
    __tablename__ = "telegram_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str | None] = mapped_column(String(200))
    # Preferencias de alertas
    languages: Mapped[str] = mapped_column(String(20), default="EN,ES")
    categories: Mapped[str | None] = mapped_column(Text)  # CSV de slugs; null = todas
    min_discount_pct: Mapped[int] = mapped_column(Integer, default=20)
    alerts_enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
