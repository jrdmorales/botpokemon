"""Adaptador HTML — FALLBACK FRÁGIL.

ADVERTENCIA: este adaptador parsea HTML con selectores CSS configurados por
tienda. Se rompe cada vez que la tienda cambia su maquetación. Usarlo SOLO
cuando la tienda no es Shopify ni WooCommerce. La alarma de "0 productos /
caída >50%" en scraper_runs existe principalmente por este adaptador.
"""

from collections.abc import AsyncIterator
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.matching.normalizer import detect_language
from app.models import Language
from app.scraping.base import ScrapedProduct, StoreAdapter
from app.scraping.keywords import looks_like_preorder
from app.scraping.price_parser import PriceParseError, parse_clp, validate_pair

MAX_PAGES = 50  # corte de seguridad contra paginación infinita


class HtmlScraperAdapter(StoreAdapter):
    async def fetch_products(self, category: str) -> AsyncIterator[ScrapedProduct]:
        if self.config.selectores is None:
            raise ValueError(f"tienda {self.config.slug}: plataforma html sin selectores")
        sel = self.config.selectores

        url: str | None = urljoin(self.config.base_url, self.config.mapeo_categorias[category])
        pages = 0
        while url and pages < MAX_PAGES:
            response = await self.client.get(url)
            soup = BeautifulSoup(response.text, "html.parser")

            for card in soup.select(sel.product):
                scraped = self._parse_card(card, category)
                if scraped is not None:
                    yield scraped

            url = None
            if sel.next_page:
                next_link = soup.select_one(sel.next_page)
                if next_link and next_link.get("href"):
                    url = urljoin(self.config.base_url, str(next_link["href"]))
            pages += 1

    def _parse_card(self, card: Tag, category: str) -> ScrapedProduct | None:
        sel = self.config.selectores
        assert sel is not None

        name_el = card.select_one(sel.name)
        link_el = card.select_one(sel.url)
        price_el = card.select_one(sel.price)
        if name_el is None or link_el is None or price_el is None:
            return None  # tarjeta incompleta (banner, placeholder, etc.)

        raw_name = name_el.get_text(strip=True)
        url = urljoin(self.config.base_url, str(link_el.get("href", "")))

        errors: list[str] = []
        suspicious = False
        try:
            price = parse_clp(price_el.get_text(strip=True), self._max_price(category))
        except PriceParseError as exc:
            return ScrapedProduct(
                store_sku=url,
                raw_name=raw_name,
                url=url,
                price=0,
                category_slug=category,
                suspicious=True,
                parse_errors=[str(exc)],
            )

        sale_price = None
        if sel.sale_price:
            sale_el = card.select_one(sel.sale_price)
            if sale_el is not None:
                try:
                    sale = parse_clp(sale_el.get_text(strip=True), self._max_price(category))
                    if validate_pair(price, sale):
                        sale_price = sale
                    else:
                        suspicious = True
                        errors.append(f"oferta {sale} > normal {price}")
                except PriceParseError as exc:
                    errors.append(f"precio oferta: {exc}")

        in_stock = True
        if sel.out_of_stock and card.select_one(sel.out_of_stock) is not None:
            in_stock = False

        structured_preorder = bool(
            sel.preorder_badge and card.select_one(sel.preorder_badge) is not None
        )

        image_url = None
        if sel.image:
            img = card.select_one(sel.image)
            if img is not None:
                src = img.get("src") or img.get("data-src")
                if src:
                    image_url = urljoin(self.config.base_url, str(src))

        language = detect_language(raw_name)
        if language == Language.UNKNOWN:
            language = self.config.idioma_default

        return ScrapedProduct(
            # Sin SKU expuesto en HTML: la URL del producto es el identificador estable
            store_sku=url,
            raw_name=raw_name,
            url=url,
            image_url=image_url,
            price=price,
            sale_price=sale_price,
            category_slug=category,
            language=language,
            in_stock=in_stock,
            is_preorder=structured_preorder or looks_like_preorder(raw_name),
            preorder_confidence_high=structured_preorder,
            suspicious=suspicious,
            parse_errors=errors,
        )
