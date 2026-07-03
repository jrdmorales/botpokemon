"""Tests de deduplicación de alertas y regla de mínimo histórico.

Sin dedup, cada escaneo de 6h re-enviaría todas las alertas.
Sin la regla de 14 días, el día 1 todo producto está en "mínimo histórico".
"""

from datetime import UTC, datetime, timedelta

from app.models import Language, Listing, ListingStatus, Platform, PriceHistory, Store
from app.services.alerts import collect_deal_alerts
from app.services.deals import evaluate_listing


async def _setup_listing(session, price=50000, sale_price=None) -> Listing:
    store = Store(
        slug="tienda-test", name="Tienda Test", base_url="https://t.cl", platform=Platform.SHOPIFY
    )
    session.add(store)
    await session.flush()
    listing = Listing(
        store_id=store.id,
        store_sku="sku-1",
        raw_name="ETB Test Inglés",
        language=Language.EN,
        url="https://t.cl/p/1",
        status=ListingStatus.ACTIVE,
        current_price=price,
        current_sale_price=sale_price,
        last_seen_at=datetime.now(UTC),
    )
    session.add(listing)
    await session.flush()
    return listing


def _history(listing_id: int, price: int, days_ago: float) -> PriceHistory:
    return PriceHistory(
        listing_id=listing_id,
        price=price,
        availability=ListingStatus.ACTIVE,
        recorded_at=datetime.now(UTC) - timedelta(days=days_ago),
    )


class TestDedup:
    async def test_misma_oferta_no_se_realerta(self, session):
        listing = await _setup_listing(session, price=50000, sale_price=30000)
        for days in (20, 15, 10, 5):
            session.add(_history(listing.id, 50000, days))
        await session.flush()

        first = await collect_deal_alerts(session)
        assert len(first) >= 1  # 40% bajo el promedio: alerta

        second = await collect_deal_alerts(session)
        assert len(second) == 0  # mismo precio: silencio

    async def test_realerta_solo_si_baja_mas(self, session):
        listing = await _setup_listing(session, price=50000, sale_price=30000)
        for days in (20, 15, 10, 5):
            session.add(_history(listing.id, 50000, days))
        await session.flush()

        assert len(await collect_deal_alerts(session)) >= 1

        listing.current_sale_price = 25000  # baja aún más
        assert len(await collect_deal_alerts(session)) >= 1


class TestHistoricMin:
    async def test_sin_14_dias_no_es_minimo_historico(self, session):
        listing = await _setup_listing(session, price=40000)
        session.add(_history(listing.id, 50000, 2))  # solo 2 días de historial
        await session.flush()

        deal = await evaluate_listing(session, listing)
        assert deal is not None
        assert deal.is_historic_min is False

    async def test_con_historial_suficiente_si_es_minimo(self, session):
        listing = await _setup_listing(session, price=40000)
        for days in (20, 15, 10, 5):
            session.add(_history(listing.id, 50000, days))
        await session.flush()

        deal = await evaluate_listing(session, listing)
        assert deal is not None
        assert deal.is_historic_min is True

    async def test_listing_sospechoso_nunca_alerta(self, session):
        listing = await _setup_listing(session, price=40000)
        listing.suspicious = True
        for days in (20, 15):
            session.add(_history(listing.id, 50000, days))
        await session.flush()

        assert await evaluate_listing(session, listing) is None
