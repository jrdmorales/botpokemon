"""Orquestación de scrapes: persiste listings, historial, preventas y salud.

Reglas que implementa (ver instrucciones.md):
- price_history: insertar solo en cambio + checkpoint diario. Nunca sobrescribir.
- Ciclo de vida: activo / sin_stock / no_visto / descontinuado.
- Transición preventa -> stock regular sin duplicar producto.
- Salud: scraper_runs + detección de caídas anómalas de productos.
"""

from datetime import UTC, date, datetime, timedelta

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.matching.matcher import match_listing
from app.models import (
    Language,
    Listing,
    ListingStatus,
    Platform,
    Preorder,
    PreorderConfidence,
    PreorderStatus,
    PriceHistory,
    ScraperRun,
    Store,
)
from app.scraping.base import ScrapedProduct, StoreBlockedError, StoreConfig
from app.scraping.config_loader import build_adapter

log = structlog.get_logger()


async def _get_or_create_store(session: AsyncSession, config: StoreConfig) -> Store:
    store = await session.scalar(select(Store).where(Store.slug == config.slug))
    if store is None:
        store = Store(
            slug=config.slug,
            name=config.nombre,
            base_url=config.base_url,
            platform=Platform(config.plataforma),
        )
        session.add(store)
        await session.flush()
    return store


def _status_for(item: ScrapedProduct) -> ListingStatus:
    if item.is_preorder:
        return ListingStatus.PREORDER
    if not item.in_stock:
        return ListingStatus.OUT_OF_STOCK
    return ListingStatus.ACTIVE


async def _record_price(
    session: AsyncSession, listing: Listing, item: ScrapedProduct, status: ListingStatus
) -> bool:
    """Inserta en price_history si cambió algo, o checkpoint diario. Devuelve True si cambió."""
    changed = (
        listing.current_price != item.price
        or listing.current_sale_price != item.sale_price
        or listing.status != status
    )
    if changed:
        session.add(
            PriceHistory(
                listing_id=listing.id,
                price=item.price,
                sale_price=item.sale_price,
                availability=status,
            )
        )
        return True

    today_start = datetime.combine(date.today(), datetime.min.time(), tzinfo=UTC)
    has_today = await session.scalar(
        select(func.count())
        .select_from(PriceHistory)
        .where(PriceHistory.listing_id == listing.id, PriceHistory.recorded_at >= today_start)
    )
    if not has_today:
        session.add(
            PriceHistory(
                listing_id=listing.id,
                price=item.price,
                sale_price=item.sale_price,
                availability=status,
                is_checkpoint=True,
            )
        )
    return False


async def _upsert_preorder(session: AsyncSession, listing: Listing, item: ScrapedProduct) -> None:
    preorder = await session.scalar(select(Preorder).where(Preorder.listing_id == listing.id))
    if item.is_preorder:
        if preorder is None:
            confidence = (
                PreorderConfidence.HIGH
                if item.preorder_confidence_high
                else PreorderConfidence.LOW
            )
            session.add(
                Preorder(
                    listing_id=listing.id,
                    confidence=confidence,
                    status=(
                        PreorderStatus.ACTIVE
                        if confidence == PreorderConfidence.HIGH
                        else PreorderStatus.PENDING_REVIEW
                    ),
                )
            )
    elif preorder is not None and preorder.status in (
        PreorderStatus.ACTIVE,
        PreorderStatus.PENDING_REVIEW,
    ):
        # Transición preventa -> stock regular: registrar, no duplicar
        preorder.status = PreorderStatus.RELEASED
        preorder.released_at = datetime.now(UTC)


async def scrape_store(session: AsyncSession, config: StoreConfig) -> ScraperRun:
    store = await _get_or_create_store(session, config)
    run = ScraperRun(store_id=store.id)
    session.add(run)
    await session.flush()

    adapter = build_adapter(config)
    seen_skus: set[str] = set()
    errors: list[str] = []
    now = datetime.now(UTC)

    try:
        async for item in adapter.fetch_all():
            if item.suspicious and item.price == 0:
                errors.append(f"{item.raw_name}: {'; '.join(item.parse_errors)}")
                continue
            seen_skus.add(item.store_sku)

            listing = await session.scalar(
                select(Listing).where(
                    Listing.store_id == store.id, Listing.store_sku == item.store_sku
                )
            )
            status = _status_for(item)
            if listing is None:
                listing = Listing(
                    store_id=store.id,
                    store_sku=item.store_sku,
                    raw_name=item.raw_name,
                    description=item.description,
                    category_slug=item.category_slug,
                    language=item.language,
                    url=item.url,
                    image_url=item.image_url,
                    status=status,
                    current_price=item.price,
                    current_sale_price=item.sale_price,
                    suspicious=item.suspicious,
                    last_seen_at=now,
                )
                session.add(listing)
                await session.flush()
                session.add(
                    PriceHistory(
                        listing_id=listing.id,
                        price=item.price,
                        sale_price=item.sale_price,
                        availability=status,
                    )
                )
                result = await match_listing(session, listing)
                if result.product is not None:
                    listing.canonical_product_id = result.product.id
            else:
                await _record_price(session, listing, item, status)
                listing.raw_name = item.raw_name
                listing.current_price = item.price
                listing.current_sale_price = item.sale_price
                listing.status = status
                listing.suspicious = item.suspicious
                listing.consecutive_misses = 0
                listing.last_seen_at = now
                if listing.language == Language.UNKNOWN:
                    listing.language = item.language
                if listing.canonical_product_id is None:
                    result = await match_listing(session, listing)
                    if result.product is not None:
                        listing.canonical_product_id = result.product.id

            await _upsert_preorder(session, listing, item)
            if item.parse_errors:
                errors.extend(f"{item.raw_name}: {e}" for e in item.parse_errors)

        await _mark_missing(session, store.id, seen_skus)
        run.products_found = len(seen_skus)
        run.success = True
        store.last_successful_scrape = now
    except StoreBlockedError as exc:
        errors.append(f"BLOQUEO: {exc} — tienda pausada, revisar manualmente")
        log.error("store_blocked", store=config.slug, error=str(exc))
    except Exception as exc:  # noqa: BLE001 — un scrape fallido no debe botar el worker
        errors.append(str(exc))
        log.error("scrape_failed", store=config.slug, error=str(exc))
    finally:
        await adapter.aclose()
        run.finished_at = datetime.now(UTC)
        run.errors = "\n".join(errors) if errors else None
        await session.commit()

    return run


async def _mark_missing(session: AsyncSession, store_id: int, seen_skus: set[str]) -> None:
    """Listings no vistos en este scrape: no_visto; tras N scrapes, descontinuado."""
    settings = get_settings()
    missing = (
        await session.scalars(
            select(Listing).where(
                Listing.store_id == store_id,
                Listing.status != ListingStatus.DISCONTINUED,
                Listing.store_sku.notin_(seen_skus) if seen_skus else True,
            )
        )
    ).all()
    for listing in missing:
        listing.consecutive_misses += 1
        if listing.consecutive_misses >= settings.missing_scrapes_before_discontinued:
            listing.status = ListingStatus.DISCONTINUED
        else:
            listing.status = ListingStatus.NOT_SEEN


async def check_scraper_health(session: AsyncSession, run: ScraperRun) -> list[str]:
    """Alarmas de salud tras un scrape. Devuelve mensajes para el canal admin."""
    alerts: list[str] = []
    store = await session.get(Store, run.store_id)
    name = store.slug if store else f"store#{run.store_id}"

    if not run.success:
        alerts.append(f"❌ Scrape FALLIDO en {name}: {run.errors or 'sin detalle'}")
        return alerts

    if run.products_found == 0:
        alerts.append(f"⚠️ {name}: 0 productos — probable cambio de HTML o bloqueo")
        return alerts

    week_ago = datetime.now(UTC) - timedelta(days=7)
    avg = await session.scalar(
        select(func.avg(ScraperRun.products_found)).where(
            ScraperRun.store_id == run.store_id,
            ScraperRun.success.is_(True),
            ScraperRun.started_at >= week_ago,
            ScraperRun.id != run.id,
        )
    )
    if avg and run.products_found < float(avg) * 0.5:
        alerts.append(
            f"⚠️ {name}: {run.products_found} productos vs promedio 7d {float(avg):.0f} "
            "(caída >50%, revisar selectores)"
        )
    return alerts
