"""Adaptador Shopify: usa /collections/{handle}/products.json.

Endpoint público estable, paginación ?page=N, máximo 250 productos por página.
Preferido sobre HTML siempre que la tienda sea Shopify.
"""

from collections.abc import AsyncIterator

from app.matching.normalizer import detect_language
from app.models import Language
from app.scraping.base import ScrapedProduct, StoreAdapter
from app.scraping.keywords import looks_like_preorder
from app.scraping.price_parser import PriceParseError, parse_clp, validate_pair

PAGE_SIZE = 250


class ShopifyAdapter(StoreAdapter):
    async def fetch_products(self, category: str) -> AsyncIterator[ScrapedProduct]:
        handle = self.config.mapeo_categorias[category]
        page = 1
        while True:
            url = (
                f"{self.config.base_url}/collections/{handle}/products.json"
                f"?limit={PAGE_SIZE}&page={page}"
            )
            response = await self.client.get(url)
            products = response.json().get("products", [])
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
        variants = product.get("variants") or []
        if not variants:
            return None
        variant = variants[0]

        errors: list[str] = []
        suspicious = False
        try:
            # En Shopify, si hay oferta: price = precio rebajado,
            # compare_at_price = precio normal.
            price_now = parse_clp(variant.get("price"), self._max_price(category))
        except PriceParseError as exc:
            errors.append(str(exc))
            return ScrapedProduct(
                store_sku=str(product["id"]),
                raw_name=product.get("title", ""),
                url=f"{self.config.base_url}/products/{product.get('handle', '')}",
                price=0,
                category_slug=category,
                suspicious=True,
                parse_errors=errors,
            )

        compare_at = variant.get("compare_at_price")
        price, sale_price = price_now, None
        if compare_at:
            try:
                normal = parse_clp(compare_at, self._max_price(category))
                if validate_pair(normal, price_now):
                    price, sale_price = normal, price_now
                else:
                    suspicious = True
                    errors.append(f"compare_at_price {normal} < price {price_now}")
            except PriceParseError as exc:
                errors.append(f"compare_at_price: {exc}")

        tags = [t.strip().lower() for t in self._tags(product)]
        marker = (self.config.preventa_marker or "").lower()
        structured_preorder = bool(marker) and marker in tags
        keyword_preorder = looks_like_preorder(product.get("title", ""))

        title = product.get("title", "")
        language = detect_language(title)
        if language == Language.UNKNOWN:
            language = self.config.idioma_default

        images = product.get("images") or []
        return ScrapedProduct(
            store_sku=str(product["id"]),
            raw_name=title,
            description=product.get("body_html"),
            url=f"{self.config.base_url}/products/{product.get('handle', '')}",
            image_url=images[0].get("src") if images else None,
            price=price,
            sale_price=sale_price,
            category_slug=category,
            language=language,
            in_stock=bool(variant.get("available", True)),
            is_preorder=structured_preorder or keyword_preorder,
            preorder_confidence_high=structured_preorder,
            suspicious=suspicious,
            parse_errors=errors,
        )

    @staticmethod
    def _tags(product: dict) -> list[str]:
        tags = product.get("tags", [])
        if isinstance(tags, str):
            return tags.split(",")
        return tags
