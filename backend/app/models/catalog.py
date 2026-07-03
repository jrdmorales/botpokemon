import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Platform(enum.StrEnum):
    SHOPIFY = "shopify"
    WOOCOMMERCE = "woocommerce"
    HTML = "html"


class Language(enum.StrEnum):
    EN = "EN"
    ES = "ES"
    UNKNOWN = "unknown"


class ListingStatus(enum.StrEnum):
    ACTIVE = "activo"
    OUT_OF_STOCK = "sin_stock"
    NOT_SEEN = "no_visto"
    DISCONTINUED = "descontinuado"
    PREORDER = "preventa"


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    base_url: Mapped[str] = mapped_column(String(500))
    platform: Mapped[Platform] = mapped_column(Enum(Platform, native_enum=False))
    last_successful_scrape: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    listings: Mapped[list["Listing"]] = relationship(back_populates="store")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    # Tope de precio para validación de parsing (CLP); null = sin tope
    max_sane_price: Mapped[int | None] = mapped_column(Integer)


class CanonicalProduct(Base):
    __tablename__ = "canonical_products"
    __table_args__ = (
        UniqueConstraint("normalized_name", "language", name="uq_canonical_name_lang"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    normalized_name: Mapped[str] = mapped_column(String(500), index=True)
    display_name: Mapped[str] = mapped_column(String(500))
    set_code: Mapped[str | None] = mapped_column(String(50), index=True)
    product_type: Mapped[str | None] = mapped_column(String(50))
    language: Mapped[Language] = mapped_column(Enum(Language, native_enum=False))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    image_url: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    listings: Mapped[list["Listing"]] = relationship(back_populates="canonical_product")


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        UniqueConstraint("store_id", "store_sku", name="uq_listing_store_sku"),
        Index("ix_listings_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    canonical_product_id: Mapped[int | None] = mapped_column(
        ForeignKey("canonical_products.id"), index=True
    )
    store_sku: Mapped[str] = mapped_column(String(200))
    raw_name: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    category_slug: Mapped[str | None] = mapped_column(String(100))
    language: Mapped[Language] = mapped_column(
        Enum(Language, native_enum=False), default=Language.UNKNOWN
    )
    url: Mapped[str] = mapped_column(String(1000))
    image_url: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[ListingStatus] = mapped_column(
        Enum(ListingStatus, native_enum=False), default=ListingStatus.ACTIVE
    )
    # Precios actuales (cache del último punto de price_history)
    current_price: Mapped[int | None] = mapped_column(Integer)
    current_sale_price: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="CLP")
    suspicious: Mapped[bool] = mapped_column(default=False)
    consecutive_misses: Mapped[int] = mapped_column(Integer, default=0)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    store: Mapped["Store"] = relationship(back_populates="listings")
    canonical_product: Mapped["CanonicalProduct | None"] = relationship(back_populates="listings")
