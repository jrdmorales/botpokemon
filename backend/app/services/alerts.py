"""Generación y deduplicación de alertas.

Regla central: nunca re-alertar el mismo evento. Se consulta alerts_sent y solo
se re-alerta si el precio bajó respecto a la última alerta enviada (trigger_price).
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import (
    AlertSent,
    AlertType,
    Listing,
    Preorder,
    PreorderConfidence,
    PreorderStatus,
    Store,
)
from app.services.deals import Deal, evaluate_listing


@dataclass
class PendingAlert:
    alert_type: AlertType
    listing: Listing
    store: Store
    price: int
    previous_price: float | None
    discount_pct: float | None


async def _already_sent(
    session: AsyncSession, alert_type: AlertType, listing_id: int, price: int
) -> bool:
    """True si ya se alertó este evento y el precio no ha bajado desde entonces."""
    last = await session.scalar(
        select(AlertSent)
        .where(AlertSent.alert_type == alert_type, AlertSent.listing_id == listing_id)
        .order_by(AlertSent.sent_at.desc())
        .limit(1)
    )
    if last is None:
        return False
    return last.trigger_price is None or price >= last.trigger_price


async def _register(
    session: AsyncSession, alert_type: AlertType, listing_id: int, price: int | None
) -> None:
    session.add(AlertSent(alert_type=alert_type, listing_id=listing_id, trigger_price=price))


async def collect_deal_alerts(session: AsyncSession) -> list[PendingAlert]:
    """Recorre listings activos y junta alertas pendientes, ya deduplicadas."""
    settings = get_settings()
    pending: list[PendingAlert] = []

    listings = (
        await session.scalars(
            select(Listing).where(Listing.suspicious.is_(False), Listing.current_price.isnot(None))
        )
    ).all()

    for listing in listings:
        deal: Deal | None = await evaluate_listing(session, listing)
        if deal is None:
            continue
        store = await session.get(Store, listing.store_id)
        if store is None:
            continue

        if deal.discount_pct >= settings.deal_alert_min_discount_pct and not await _already_sent(
            session, AlertType.DEAL, listing.id, deal.effective_price
        ):
            pending.append(
                PendingAlert(
                    alert_type=AlertType.DEAL,
                    listing=listing,
                    store=store,
                    price=deal.effective_price,
                    previous_price=deal.baseline_avg,
                    discount_pct=deal.discount_pct,
                )
            )
            await _register(session, AlertType.DEAL, listing.id, deal.effective_price)

        if deal.is_historic_min and not await _already_sent(
            session, AlertType.HISTORIC_MIN, listing.id, deal.effective_price
        ):
            pending.append(
                PendingAlert(
                    alert_type=AlertType.HISTORIC_MIN,
                    listing=listing,
                    store=store,
                    price=deal.effective_price,
                    previous_price=deal.baseline_avg,
                    discount_pct=deal.discount_pct,
                )
            )
            await _register(session, AlertType.HISTORIC_MIN, listing.id, deal.effective_price)

    return pending


async def collect_preorder_alerts(session: AsyncSession) -> list[PendingAlert]:
    """Preventas nuevas con confianza ALTA. Las de keywords esperan revisión manual."""
    pending: list[PendingAlert] = []
    preorders = (
        await session.scalars(
            select(Preorder).where(
                Preorder.status == PreorderStatus.ACTIVE,
                Preorder.confidence == PreorderConfidence.HIGH,
            )
        )
    ).all()

    for preorder in preorders:
        listing = await session.get(Listing, preorder.listing_id)
        if listing is None or listing.current_price is None:
            continue
        if await _already_sent(session, AlertType.NEW_PREORDER, listing.id, listing.current_price):
            continue
        store = await session.get(Store, listing.store_id)
        if store is None:
            continue
        pending.append(
            PendingAlert(
                alert_type=AlertType.NEW_PREORDER,
                listing=listing,
                store=store,
                price=listing.current_price,
                previous_price=None,
                discount_pct=None,
            )
        )
        await _register(session, AlertType.NEW_PREORDER, listing.id, listing.current_price)

    return pending


def format_alert(alert: PendingAlert) -> str:
    """Formato del mensaje de Telegram (ver instrucciones.md)."""
    titles = {
        AlertType.NEW_PREORDER: "🆕 Nueva preventa",
        AlertType.DEAL: "🔥 Oferta",
        AlertType.HISTORIC_MIN: "📉 Mínimo histórico",
    }
    lines = [
        f"{titles[alert.alert_type]}",
        f"{alert.listing.raw_name} [{alert.listing.language}]",
        f"Tienda: {alert.store.name}",
        f"Precio: ${alert.price:,} CLP".replace(",", "."),
    ]
    if alert.previous_price:
        lines.append(f"Promedio 30d: ${int(alert.previous_price):,} CLP".replace(",", "."))
    if alert.discount_pct:
        lines.append(f"Descuento real: {alert.discount_pct:.0f}%")
    lines.append(alert.listing.url)
    return "\n".join(lines)
