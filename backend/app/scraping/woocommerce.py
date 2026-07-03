"""Adaptador WooCommerce: usa la Store API pública.

GET /wp-json/wc/store/v1/products?category={slug}&page=N&per_page=100
Los precios vienen en minor units con currency_minor_unit (CLP usa 0).
"""

from collections.abc import AsyncIterator

from app.matching.normalizer import detect_language
from app.models import Language
from app.scraping.base import ScrapedProduct, StoreAdapter
from app.scraping.keywords import looks_like_preorder
from app.scraping.price_parser import PriceParseError, parse_clp, validate_pair

PAGE_SIZE = 100


class WooCommerceAdapter(StoreAdapter):
    async def fetch_products(self, category: str) -> AsyncIterator[ScrapedProduct]:
        category_id = self.config.mapeo_categorias[category]
        page = 1
        while True:
            # category_id puede ser ID numérico o slug — la API acepta ambos
            url = (
                f"{self.config.base_url}/wp-json/wc/store/v1/products"
                f"?category={category_id}&per_page={PAGE_SIZE}&page={page}"
            )
            response = await self.client.get(url)
            products = response.json()
            if not products:
                return
            for product in products:
                scraped = self._parse(product, category)
                if scraped is not None:
                    yield scraped
            if len(products) < PAGE_SIZE:
                return
            page += 1

    def _parse(self, product: dict, category: str) -> ScrapedProduct | None:
        prices = product.get("prices") or {}
        minor_unit = int(prices.get("currency_minor_unit", 0))
        divisor = 10**minor_unit

        errors: list[str] = []
        suspicious = False
        try:
            regular = parse_clp(
                int(prices.get("regular_price", 0)) // divisor, self._max_price(category)
            )
        except (PriceParseError, ValueError) as exc:
            return ScrapedProduct(
                store_sku=str(product["id"]),
                raw_name=product.get("name", ""),
                url=product.get("permalink", ""),
                price=0,
                category_slug=category,
                suspicious=True,
                parse_errors=[str(exc)],
            )

        sale_price = None
        if product.get("on_sale"):
            try:
                sale = parse_clp(
                    int(prices.get("sale_price", 0)) // divisor, self._max_price(category)
                )
                if validate_pair(regular, sale):
                    sale_price = sale
                else:
                    suspicious = True
                    errors.append(f"sale_price {sale} > regular_price {regular}")
            except (PriceParseError, ValueError) as exc:
                errors.append(f"sale_price: {exc}")

        name = product.get("name", "")
        marker = (self.config.preventa_marker or "").lower()
        categories = [c.get("slug", "").lower() for c in product.get("categories", [])]
        tags = [t.get("slug", "").lower() for t in product.get("tags", [])]
        structured_preorder = bool(marker) and (marker in categories or marker in tags)

        language = detect_language(name)
        if language == Language.UNKNOWN:
            language = self.config.idioma_default

        images = product.get("images") or []
        return ScrapedProduct(
            store_sku=str(product["id"]),
            raw_name=name,
            description=product.get("short_description"),
            url=product.get("permalink", ""),
            image_url=images[0].get("src") if images else None,
            price=regular,
            sale_price=sale_price,
            category_slug=category,
            language=language,
            in_stock=product.get("is_in_stock", True),
            is_preorder=structured_preorder or looks_like_preorder(name),
            preorder_confidence_high=structured_preorder,
            suspicious=suspicious,
            parse_errors=errors,
        )
