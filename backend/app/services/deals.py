"""Detección de ofertas reales.

Una oferta es "real" solo si el precio actual está bajo el promedio histórico
propio (30 días). El descuento declarado por la tienda se ignora para alertas:
las tiendas inflan el precio de lista.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Listing, ListingStatus, PriceHistory


@dataclass
class Deal:
    listing: Listing
    effective_price: int
    baseline_avg: float
    discount_pct: float  # contra promedio histórico propio
    is_historic_min: bool
    history_days: float


def effective_price(listing: Listing) -> int | None:
    if listing.current_sale_price is not None:
        return listing.current_sale_price
    return listing.current_price


async def evaluate_listing(session: AsyncSession, listing: Listing) -> Deal | None:
    """Evalúa si un listing es oferta real. None si no hay datos suficientes."""
    settings = get_settings()
    price = effective_price(listing)
    if price is None or listing.suspicious:
        return None
    if listing.status not in (ListingStatus.ACTIVE, ListingStatus.PREORDER):
        return None

    now = datetime.now(UTC)
    baseline_start = now - timedelta(days=settings.deal_baseline_days)

    baseline_avg = await session.scalar(
        select(func.avg(func.coalesce(PriceHistory.sale_price, PriceHistory.price))).where(
            PriceHistory.listing_id == listing.id,
            PriceHistory.recorded_at >= baseline_start,
            PriceHistory.recorded_at < now - timedelta(hours=1),  # excluir el punto recién insertado
        )
    )
    if not baseline_avg:
        return None

    discount_pct = (float(baseline_avg) - price) / float(baseline_avg) * 100
    if discount_pct <= 0:
        return None

    first_point = await session.scalar(
        select(func.min(PriceHistory.recorded_at)).where(PriceHistory.listing_id == listing.id)
    )
    if first_point is not None and first_point.tzinfo is None:
        # SQLite (tests) devuelve datetimes naive; PostgreSQL los entrega aware
        first_point = first_point.replace(tzinfo=UTC)
    history_days = (now - first_point).total_seconds() / 86400 if first_point else 0.0

    historic_min = await session.scalar(
        select(func.min(func.coalesce(PriceHistory.sale_price, PriceHistory.price))).where(
            PriceHistory.listing_id == listing.id
        )
    )
    # Mínimo histórico válido solo con historial suficiente (evita spam día 1)
    is_historic_min = (
        historic_min is not None
        and price <= historic_min
        and history_days >= settings.historic_min_required_days
    )

    return Deal(
        listing=listing,
        effective_price=price,
        baseline_avg=float(baseline_avg),
        discount_pct=discount_pct,
        is_historic_min=is_historic_min,
        history_days=history_days,
    )
