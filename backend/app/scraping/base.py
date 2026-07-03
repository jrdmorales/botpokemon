"""Interfaz StoreAdapter y tipos compartidos del scraping.

Las tiendas se configuran como dato (YAML en backend/stores/), no como código.
Un adaptador por plataforma: Shopify, WooCommerce, HTML (fallback frágil).
"""

import asyncio
import random
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import httpx
from pydantic import BaseModel, Field

from app.config import get_settings
from app.models import Language, Platform


class HtmlSelectors(BaseModel):
    product: str
    name: str
    price: str
    sale_price: str | None = None
    url: str = "a"
    image: str | None = "img"
    out_of_stock: str | None = None
    preorder_badge: str | None = None
    next_page: str | None = None


class StoreConfig(BaseModel):
    """Esquema del YAML de configuración por tienda."""

    nombre: str
    slug: str
    base_url: str
    plataforma: Platform
    # categoria interna -> handle/slug/URL según plataforma
    mapeo_categorias: dict[str, str]
    # Detección estructurada de preventas: tag Shopify, categoría Woo, o selector CSS
    preventa_marker: str | None = None
    # Tope de precio por categoría (CLP) para validación de parsing
    max_price_por_categoria: dict[str, int] = Field(default_factory=dict)
    idioma_default: Language = Language.UNKNOWN
    selectores: HtmlSelectors | None = None  # solo plataforma html


@dataclass
class ScrapedProduct:
    store_sku: str
    raw_name: str
    url: str
    price: int
    category_slug: str
    sale_price: int | None = None
    description: str | None = None
    image_url: str | None = None
    language: Language = Language.UNKNOWN
    in_stock: bool = True
    is_preorder: bool = False
    preorder_confidence_high: bool = False
    suspicious: bool = False
    parse_errors: list[str] = field(default_factory=list)


class PoliteClient:
    """Cliente HTTP cortés: 1 request concurrente por tienda, delay aleatorio,
    retry con backoff exponencial, User-Agent honesto e identificable."""

    def __init__(self) -> None:
        settings = get_settings()
        self._delay_range = (settings.request_delay_min_s, settings.request_delay_max_s)
        self._max_retries = settings.max_retries
        self._lock = asyncio.Lock()
        self._client = httpx.AsyncClient(
            headers={"User-Agent": settings.user_agent},
            timeout=30.0,
            follow_redirects=True,
        )

    async def get(self, url: str, **kwargs) -> httpx.Response:
        async with self._lock:  # máx. 1 request en vuelo por tienda
            last_exc: Exception | None = None
            for attempt in range(self._max_retries):
                await asyncio.sleep(random.uniform(*self._delay_range))
                try:
                    response = await self._client.get(url, **kwargs)
                    if response.status_code in (403, 429):
                        # No insistir: la tienda nos está limitando.
                        raise StoreBlockedError(url, response.status_code)
                    response.raise_for_status()
                    return response
                except StoreBlockedError:
                    raise
                except httpx.HTTPError as exc:
                    last_exc = exc
                    await asyncio.sleep(2**attempt)
            raise last_exc  # type: ignore[misc]

    async def aclose(self) -> None:
        await self._client.aclose()


class StoreBlockedError(Exception):
    """La tienda respondió 403/429: pausar la tienda y alertar al admin, no evadir."""

    def __init__(self, url: str, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"{status_code} en {url}")


class StoreAdapter(ABC):
    def __init__(self, config: StoreConfig, client: PoliteClient | None = None) -> None:
        self.config = config
        self.client = client or PoliteClient()

    @abstractmethod
    def fetch_products(self, category: str) -> AsyncIterator[ScrapedProduct]:
        """Itera los productos de una categoría (slug interno del sistema)."""

    async def fetch_all(self) -> AsyncIterator[ScrapedProduct]:
        for category in self.config.mapeo_categorias:
            async for product in self.fetch_products(category):
                yield product

    async def aclose(self) -> None:
        await self.client.aclose()

    def _max_price(self, category: str) -> int | None:
        return self.config.max_price_por_categoria.get(category)
