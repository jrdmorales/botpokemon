"""Worker de scraping: APScheduler orquesta los escaneos periódicos.

- Escaneo completo cada 6 horas (jitter para no golpear todas las tiendas a la vez)
- Escaneo rápido de preventas cada 1 hora
- Tras cada scrape: chequeo de salud + envío de alertas vía Telegram
"""

import asyncio

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.db import SessionLocal
from app.scraping.config_loader import load_store_configs
from app.scraping.runner import check_scraper_health, scrape_store
from app.services.alerts import collect_deal_alerts, collect_preorder_alerts, format_alert
from app.telegram.notifier import broadcast_alert, notify_admin

log = structlog.get_logger()


async def full_scan() -> None:
    configs = load_store_configs()
    log.info("full_scan_start", stores=[c.slug for c in configs])
    for config in configs:
        async with SessionLocal() as session:
            run = await scrape_store(session, config)
            for message in await check_scraper_health(session, run):
                await notify_admin(message)
            log.info("scraped", store=config.slug, products=run.products_found, ok=run.success)

    async with SessionLocal() as session:
        alerts = await collect_deal_alerts(session)
        alerts += await collect_preorder_alerts(session)
        await session.commit()
    for alert in alerts:
        await broadcast_alert(alert, format_alert(alert))
    log.info("full_scan_done", alerts_sent=len(alerts))

    # Notificar al admin con resumen del scan
    from app.db import SessionLocal as SL
    from app.models import Listing, ScraperRun, Store
    from sqlalchemy import func as sqlfunc, select as sqsel

    lines = ["✅ *Scan completo finalizado*\n"]
    async with SL() as session:
        stores = (await session.scalars(sqsel(Store).order_by(Store.name))).all()
        total = 0
        for store in stores:
            run = await session.scalar(
                sqsel(ScraperRun)
                .where(ScraperRun.store_id == store.id)
                .order_by(ScraperRun.started_at.desc())
                .limit(1)
            )
            count = await session.scalar(
                sqsel(sqlfunc.count(Listing.id)).where(Listing.store_id == store.id)
            )
            if run:
                icon = "✅" if run.success else "❌"
                lines.append(f"{icon} {store.name}: {run.products_found} scrapeados ({count} total)")
                total += count
        lines.append(f"\n📦 Total en BD: {total} productos")
        lines.append(f"🔔 Alertas enviadas: {len(alerts)}")
    await notify_admin("\n".join(lines))


async def preorder_scan() -> None:
    """Escaneo rápido: solo categorías con preventas (las marcadas en config)."""
    configs = [c for c in load_store_configs() if c.preventa_marker]
    for config in configs:
        async with SessionLocal() as session:
            run = await scrape_store(session, config)
            log.info("preorder_scan", store=config.slug, ok=run.success)

    async with SessionLocal() as session:
        alerts = await collect_preorder_alerts(session)
        await session.commit()
    for alert in alerts:
        await broadcast_alert(alert, format_alert(alert))


async def main() -> None:
    settings = get_settings()

    # Bootstrap idempotente de tablas (por si el worker arranca antes que el API)
    from app.db import ensure_schema

    await ensure_schema()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        full_scan,
        "interval",
        hours=settings.scrape_full_interval_hours,
        jitter=600,  # ±10 min para no escanear siempre a la misma hora exacta
        next_run_time=None,
    )
    scheduler.add_job(
        preorder_scan,
        "interval",
        hours=settings.scrape_preorder_interval_hours,
        jitter=300,
    )
    scheduler.start()
    log.info("worker_started")

    await full_scan()  # primer escaneo inmediato al arrancar
    await asyncio.Event().wait()  # mantener vivo


if __name__ == "__main__":
    asyncio.run(main())
