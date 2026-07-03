from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class StoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    base_url: str
    platform: str
    last_successful_scrape: datetime | None


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    store_name: str
    raw_name: str
    language: str
    url: str
    image_url: str | None
    status: str
    current_price: int | None
    current_sale_price: int | None
    currency: str
    last_seen_at: datetime | None
    is_stale: bool  # datos viejos (> stale_data_hours): atenuar en el frontend


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str
    set_code: str | None
    product_type: str | None
    language: str
    image_url: str | None
    best_price: int | None = None
    best_price_store: str | None = None


class ProductDetailOut(ProductOut):
    listings: list[ListingOut] = []


class DealOut(BaseModel):
    listing: ListingOut
    effective_price: int
    baseline_avg: float
    discount_pct: float
    is_historic_min: bool


class PreorderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    listing: ListingOut
    detected_at: datetime
    release_date: datetime | None
    confidence: str


class PricePointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    price: int
    sale_price: int | None
    availability: str
    recorded_at: datetime


class PriceHistoryOut(BaseModel):
    store_name: str
    listing_id: int
    points: list[PricePointOut]
    min_price: int | None
    max_price: int | None
    avg_price: float | None


class MatchReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    listing_id: int
    listing_name: str
    candidate_product_id: int
    candidate_name: str
    score: int
    status: str


class Paginated(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    per_page: int
