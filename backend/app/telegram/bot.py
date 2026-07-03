"""Bot de Telegram: comandos /ofertas /preventas /mejores /buscar /alertas /comparar /estado."""

from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from app.config import get_settings
from app.db import SessionLocal
from app.models import (
    CanonicalProduct,
    Listing,
    Preorder,
    PreorderConfidence,
    PreorderStatus,
    ScraperRun,
    Store,
    TelegramUser,
)
from app.services.deals import evaluate_listing

log = structlog.get_logger()

MAX_RESULTS = 10


def _fmt_price(value: int | float) -> str:
    return f"${int(value):,} CLP".replace(",", ".")


async def _ensure_user(update: Update) -> None:
    if update.effective_chat is None:
        return
    async with SessionLocal() as session:
        user = await session.scalar(
            select(TelegramUser).where(TelegramUser.chat_id == update.effective_chat.id)
        )
        if user is None:
            session.add(
                TelegramUser(
                    chat_id=update.effective_chat.id,
                    username=update.effective_user.username if update.effective_user else None,
                )
            )
            await session.commit()


async def cmd_start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await _ensure_user(update)
    await update.message.reply_text(
        "👋 PokePrecio: monitor de precios Pokémon TCG en tiendas chilenas.\n\n"
        "/ofertas — ofertas reales del día\n"
        "/preventas — preventas activas\n"
        "/mejores — mayores descuentos\n"
        "/buscar <texto> — buscar producto\n"
        "/alertas — configurar alertas automáticas\n"
        "/comparar <producto> — comparar precios entre tiendas\n"
        "/estado — estado de scrapers por tienda"
    )


async def _top_deals(limit: int, min_discount: float) -> list[str]:
    lines = []
    async with SessionLocal() as session:
        listings = (
            await session.scalars(
                select(Listing).where(
                    Listing.suspicious.is_(False), Listing.current_price.isnot(None)
                )
            )
        ).all()
        deals = []
        for listing in listings:
            deal = await evaluate_listing(session, listing)
            if deal is not None and deal.discount_pct >= min_discount:
                deals.append(deal)
        deals.sort(key=lambda d: d.discount_pct, reverse=True)
        for deal in deals[:limit]:
            store = await session.get(Store, deal.listing.store_id)
            lines.append(
                f"🔥 {deal.listing.raw_name} [{deal.listing.language}]\n"
                f"   {store.name if store else '?'} — {_fmt_price(deal.effective_price)} "
                f"(-{deal.discount_pct:.0f}%)\n   {deal.listing.url}"
            )
    return lines


async def cmd_ofertas(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await _ensure_user(update)
    lines = await _top_deals(MAX_RESULTS, get_settings().deal_alert_min_discount_pct)
    await update.message.reply_text(
        "\n\n".join(lines) if lines else "Sin ofertas reales por ahora 😴"
    )


async def cmd_mejores(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await _ensure_user(update)
    lines = await _top_deals(MAX_RESULTS, 5.0)
    await update.message.reply_text(
        "\n\n".join(lines) if lines else "Sin descuentos destacables por ahora 😴"
    )


async def cmd_preventas(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await _ensure_user(update)
    lines = []
    async with SessionLocal() as session:
        preorders = (
            await session.scalars(
                select(Preorder)
                .where(
                    Preorder.status == PreorderStatus.ACTIVE,
                    Preorder.confidence == PreorderConfidence.HIGH,
                )
                .limit(MAX_RESULTS)
            )
        ).all()
        for preorder in preorders:
            listing = await session.get(Listing, preorder.listing_id)
            if listing is None:
                continue
            store = await session.get(Store, listing.store_id)
            price = listing.current_sale_price or listing.current_price
            lines.append(
                f"🆕 {listing.raw_name} [{listing.language}]\n"
                f"   {store.name if store else '?'} — "
                f"{_fmt_price(price) if price else 'precio n/d'}\n   {listing.url}"
            )
    await update.message.reply_text(
        "\n\n".join(lines) if lines else "Sin preventas activas por ahora"
    )


async def cmd_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _ensure_user(update)
    query = " ".join(context.args or [])
    if not query:
        await update.message.reply_text("Uso: /buscar <nombre del producto>")
        return
    lines = []
    async with SessionLocal() as session:
        products = (
            await session.scalars(
                select(CanonicalProduct)
                .where(CanonicalProduct.normalized_name.ilike(f"%{query.lower()}%"))
                .limit(MAX_RESULTS)
            )
        ).all()
        for product in products:
            listings = (
                await session.scalars(
                    select(Listing).where(
                        Listing.canonical_product_id == product.id,
                        Listing.current_price.isnot(None),
                    )
                )
            ).all()
            prices = [
                item.current_sale_price or item.current_price for item in listings
            ]
            best = min(prices) if prices else None
            lines.append(
                f"• {product.display_name} [{product.language}] — "
                f"{'desde ' + _fmt_price(best) if best else 'sin precio'} "
                f"({len(listings)} tiendas)"
            )
    await update.message.reply_text("\n".join(lines) if lines else f"Sin resultados para {query!r}")


# Categorías selladas — excluye singles/cartas sueltas
_SEALED_CATEGORIES = {
    "etb": "Elite Trainer Box",
    "booster_box": "Booster Box",
    "booster_pack": "Booster Pack",
    "booster_bundle": "Booster Bundle",
    "collection_box": "Collection Box",
    "tin": "Tin",
    "blisters": "Blisters",
    "accesorios": "Accesorios",
}

# Slugs de categoría que son singles — siempre excluir del comparador
_SINGLES_SLUGS = {
    "pokemon-singles", "singles", "cartas-sueltas", "cartas-pokemon",
    "lotes-de-cartas", "cartas-pokemon-chile", "cartas-pokemon-en-espanol",
    "comprar-cartas-pokemon-en-ingles", "pokemon_en", "pokemon_es",
    "todos-los-productos-singles",
}


def _sealed_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(label, callback_data=f"cmp:{slug}")]
        for slug, label in _SEALED_CATEGORIES.items()
    ]
    return InlineKeyboardMarkup(buttons)


async def _show_comparar_by_category(query_cb, category_slug: str) -> None:
    label = _SEALED_CATEGORIES.get(category_slug, category_slug)
    async with SessionLocal() as session:
        listings = (
            await session.scalars(
                select(Listing).where(
                    Listing.category_slug == category_slug,
                    Listing.status.in_(["activo", "preventa"]),
                    Listing.current_price.isnot(None),
                    Listing.category_slug.notin_(_SINGLES_SLUGS),
                )
            )
        ).all()

        if not listings:
            await query_cb.edit_message_text(f"Sin stock activo en {label}.")
            return

        # Agrupar por canonical_product_id, tomar mejor precio por producto
        from collections import defaultdict
        by_product: dict[int | None, list[Listing]] = defaultdict(list)
        for lst in listings:
            by_product[lst.canonical_product_id].append(lst)

        # Ordenar productos por su mejor precio
        product_best: list[tuple[int, list[Listing]]] = []
        for listings_group in by_product.values():
            best_price = min(
                l.current_sale_price or l.current_price or 999_999_999
                for l in listings_group
            )
            product_best.append((best_price, listings_group))
        product_best.sort(key=lambda x: x[0])

        lines = [f"🏷 *{label}* — mejores precios\n"]
        shown = 0
        for best_price, listings_group in product_best[:8]:
            # Nombre desde el primer listing del grupo
            name = listings_group[0].raw_name
            lines.append(f"🃏 *{name[:50]}*")
            ranked = sorted(
                listings_group,
                key=lambda l: l.current_sale_price or l.current_price or 999_999_999,
            )
            for i, lst in enumerate(ranked[:4]):
                store = await session.get(Store, lst.store_id)
                price = lst.current_sale_price or lst.current_price
                medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"  {i+1}."
                sale = " 🔥" if lst.current_sale_price else ""
                lines.append(
                    f"  {medal} {store.name if store else '?'}: {_fmt_price(price)}{sale}"
                )
            lines.append("")
            shown += 1

        if shown == 0:
            await query_cb.edit_message_text(f"Sin stock activo en {label}.")
            return

    await query_cb.edit_message_text(
        "\n".join(lines),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


async def cmd_comparar(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """/comparar — muestra menú de categorías selladas para comparar precios entre tiendas."""
    await _ensure_user(update)
    await update.message.reply_text(
        "¿Qué categoría quieres comparar?",
        reply_markup=_sealed_keyboard(),
    )


async def callback_comparar(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja la selección de categoría del teclado inline de /comparar."""
    query = update.callback_query
    await query.answer()
    if not query.data or not query.data.startswith("cmp:"):
        return
    category_slug = query.data.split(":", 1)[1]
    await _show_comparar_by_category(query, category_slug)


async def cmd_estado(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el estado del último scrape de cada tienda."""
    await _ensure_user(update)
    lines = ["📊 *Estado de scrapers*\n"]
    async with SessionLocal() as session:
        stores = (await session.scalars(select(Store).order_by(Store.name))).all()
        for store in stores:
            last_run = await session.scalar(
                select(ScraperRun)
                .where(ScraperRun.store_id == store.id)
                .order_by(ScraperRun.started_at.desc())
                .limit(1)
            )
            products = await session.scalar(
                select(func.count(Listing.id)).where(Listing.store_id == store.id)
            )
            if last_run is None:
                lines.append(f"⚪ {store.name} — sin scrapes aún")
                continue

            status = "✅" if last_run.success else "❌"
            if store.last_successful_scrape:
                last = store.last_successful_scrape
                if last.tzinfo is None:
                    last = last.replace(tzinfo=UTC)
                mins = int((datetime.now(UTC) - last).total_seconds() / 60)
                age = f"{mins}m" if mins < 60 else f"{mins // 60}h {mins % 60}m"
            else:
                age = "nunca"
            lines.append(
                f"{status} *{store.name}*\n"
                f"   {products} productos · último: hace {age}"
                + (f"\n   ⚠️ {last_run.errors[:80]}" if last_run.errors else "")
            )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_alertas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Configurar preferencias: /alertas [on|off|idioma EN|ES|ambos|descuento N]"""
    await _ensure_user(update)
    args = [a.lower() for a in (context.args or [])]
    async with SessionLocal() as session:
        user = await session.scalar(
            select(TelegramUser).where(TelegramUser.chat_id == update.effective_chat.id)
        )
        if not args:
            await update.message.reply_text(
                f"Alertas: {'✅ activadas' if user.alerts_enabled else '❌ desactivadas'}\n"
                f"Idiomas: {user.languages}\n"
                f"Descuento mínimo: {user.min_discount_pct}%\n\n"
                "Configurar:\n"
                "/alertas on | off\n"
                "/alertas idioma EN | ES | ambos\n"
                "/alertas descuento 25"
            )
            return
        if args[0] == "on":
            user.alerts_enabled = True
            reply = "✅ Alertas activadas"
        elif args[0] == "off":
            user.alerts_enabled = False
            reply = "❌ Alertas desactivadas"
        elif args[0] == "idioma" and len(args) > 1:
            value = args[1].upper()
            user.languages = "EN,ES" if value == "AMBOS" else value
            reply = f"Idioma de alertas: {user.languages}"
        elif args[0] == "descuento" and len(args) > 1 and args[1].isdigit():
            user.min_discount_pct = int(args[1])
            reply = f"Descuento mínimo para alertar: {user.min_discount_pct}%"
        else:
            reply = "No entendí. Usa /alertas sin argumentos para ver opciones."
        await session.commit()
    await update.message.reply_text(reply)


def main() -> None:
    token = get_settings().telegram_bot_token
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN no configurado")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ofertas", cmd_ofertas))
    app.add_handler(CommandHandler("preventas", cmd_preventas))
    app.add_handler(CommandHandler("mejores", cmd_mejores))
    app.add_handler(CommandHandler("buscar", cmd_buscar))
    app.add_handler(CommandHandler("alertas", cmd_alertas))
    app.add_handler(CommandHandler("comparar", cmd_comparar))
    app.add_handler(CommandHandler("estado", cmd_estado))
    app.add_handler(CallbackQueryHandler(callback_comparar, pattern="^cmp:"))
    log.info("bot_started")
    app.run_polling()


if __name__ == "__main__":
    main()
