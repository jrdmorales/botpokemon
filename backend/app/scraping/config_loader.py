"""Carga y validación de configuraciones de tienda (YAML en backend/stores/).

Agregar una tienda = agregar un archivo YAML. Cero código nuevo, salvo
tiendas custom que requieren selectores para HtmlScraperAdapter.
"""

from pathlib import Path

import yaml

from app.config import get_settings
from app.models import Platform
from app.scraping.base import StoreAdapter, StoreConfig
from app.scraping.html_scraper import HtmlScraperAdapter
from app.scraping.shopify import ShopifyAdapter
from app.scraping.woocommerce import WooCommerceAdapter

_ADAPTERS: dict[Platform, type[StoreAdapter]] = {
    Platform.SHOPIFY: ShopifyAdapter,
    Platform.WOOCOMMERCE: WooCommerceAdapter,
    Platform.HTML: HtmlScraperAdapter,
}


def load_store_configs(directory: Path | None = None) -> list[StoreConfig]:
    directory = directory or get_settings().stores_config_dir
    configs = []
    for path in sorted(directory.glob("*.yaml")):
        with open(path, encoding="utf-8") as f:
            configs.append(StoreConfig.model_validate(yaml.safe_load(f)))
    return configs


def build_adapter(config: StoreConfig) -> StoreAdapter:
    return _ADAPTERS[config.plataforma](config)
