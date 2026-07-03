"""Endpoints públicos del API."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import (
    DealOut,
    ListingOut,
    Paginated,
    PreorderOut,
    PriceHistoryOut,
    PricePointOut,
    ProductDetailOut,
    ProductOut,
    StoreOut,
)
from app.config import get_settings
from app.db import get_session
from app.models import (
    CanonicalProduct,
    Listing,
    ListingStatus,
    Preorder,
    PreorderConfidence,
    PreorderStatus,
    PriceHistory,
    Store,
)
from app.services.deals import effective_price, evaluate_listing

router = APIRouter()


def _is_stale(listing: Listing) -> bool:
    if listing.last_seen_at is None:
        return True
    last = listing.last_seen_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    return datetime.now(UTC) - last > timedelta(hours=get_settings().stale_data_hours)


def _listing_out(listing: Listing, store_name: str) -> ListingOut:
    return ListingOut(
        id=listing.id,
        store_id=listing.store_id,
        store_name=store_name,
        raw_name=listing.raw_name,
        language=listing.language,
        url=listing.url,
        image_url=listing.image_url,
        status=listing.status,
        current_price=listing.current_price,
        current_sale_price=listing.current_sale_price,
        currency=listing.currency,
        last_seen_at=listing.last_seen_at,
        is_stale=_is_stale(listing),
    )


@router.get("/stores", response_model=list[StoreOut])
async def list_stores(session: AsyncSession = Depends(get_session)):
    stores = (await session.scalars(select(Store))).all()
    return stores


@router.get("/products", response_model=Paginated[ProductOut])
async def list_products(
    session: AsyncSession = Depends(get_session),
    q: str | None = None,
    language: str | None = Query(None, pattern="^(EN|ES)$"),
    product_type: str | None = None,
    set_code: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    query = select(CanonicalProduct).options(
        selectinload(CanonicalProduct.listings).selectinload(Listing.store)
    )
    if q:
        query = query.where(CanonicalProduct.normalized_name.ilike(f"%{q.lower()}%"))
    if language:
        query = query.where(CanonicalProduct.language == language)
    if product_type:
        query = query.where(CanonicalProduct.product_type == product_type)
    if set_code:
        query = query.where(CanonicalProduct.set_code == set_code)

    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    products = (await session.scalars(query.offset((page - 1) * per_page).limit(per_page))).all()

    items = []
    for product in products:
        best_price, best_store = None, None
        for listing in product.listings:
            if listing.status != ListingStatus.ACTIVE or _is_stale(listing):
                continue
            price = effective_price(listing)
            if price is not None and (best_price is None or price < best_price):
                best_price, best_store = price, listing.store.name
        items.append(
            ProductOut(
                id=product.id,
                display_name=product.display_name,
                set_code=product.set_code,
                product_type=product.product_type,
                language=product.language,
                image_url=product.image_url,
                best_price=best_price,
                best_price_store=best_store,
            )
        )
    return Paginated(items=items, total=total, page=page, per_page=per_page)


@router.get("/products/{product_id}", response_model=ProductDetailOut)
async def get_product(product_id: int, session: AsyncSession = Depends(get_session)):
    product = await session.scalar(
        select(CanonicalProduct)
        .where(CanonicalProduct.id == product_id)
        .options(selectinload(CanonicalProduct.listings).selectinload(Listing.store))
    )
    if product is None:
        raise HTTPException(404, "producto no encontrado")

    listings = [_listing_out(item, item.store.name) for item in product.listings]
    fresh_prices = [
        (item.current_sale_price or item.current_price, item.store.name)
        for item in product.listings
        if item.status == ListingStatus.ACTIVE
        and not _is_stale(item)
        and (item.current_sale_price or item.current_price) is not None
    ]
    best = min(fresh_prices, default=(None, None))
    return ProductDetailOut(
        id=product.id,
        display_name=product.display_name,
        set_code=product.set_code,
        product_type=product.product_type,
        language=product.language,
        image_url=product.image_url,
        best_price=best[0],
        best_price_store=best[1],
        listings=listings,
    )


@router.get("/deals", response_model=list[DealOut])
async def list_deals(
    session: AsyncSession = Depends(get_session),
    min_discount: float = Query(10.0, ge=0),
    language: str | None = Query(None, pattern="^(EN|ES)$"),
    store_slug: str | None = None,
    limit: int = Query(50, ge=1, le=200),
):
    query = (
        select(Listing)
        .options(selectinload(Listing.store))
        .where(
            Listing.status.in_([ListingStatus.ACTIVE, ListingStatus.PREORDER]),
            Listing.suspicious.is_(False),
            Listing.current_price.isnot(None),
        )
    )
    if language:
        query = query.where(Listing.language == language)
    if store_slug:
        query = query.join(Store).where(Store.slug == store_slug)

    deals = []
    for listing in (await session.scalars(query)).all():
        if _is_stale(listing):
            continue
        deal = await evaluate_listing(session, listing)
        if deal is None or deal.discount_pct < min_discount:
            continue
        deals.append(
            DealOut(
                listing=_listing_out(listing, listing.store.name),
                effective_price=deal.effective_price,
                baseline_avg=deal.baseline_avg,
                discount_pct=round(deal.discount_pct, 1),
                is_historic_min=deal.is_historic_min,
            )
        )
    deals.sort(key=lambda d: d.discount_pct, reverse=True)
    return deals[:limit]


@router.get("/preorders", response_model=list[PreorderOut])
async def list_preorders(session: AsyncSession = Depends(get_session)):
    preorders = (
        await session.scalars(
            select(Preorder).where(
                Preorder.status == PreorderStatus.ACTIVE,
                Preorder.confidence == PreorderConfidence.HIGH,
            )
        )
    ).all()
    out = []
    for preorder in preorders:
        listing = await session.get(Listing, preorder.listing_id)
        if listing is None:
            continue
        store = await session.get(Store, listing.store_id)
        out.append(
            PreorderOut(
                id=preorder.id,
                listing=_listing_out(listing, store.name if store else "?"),
                detected_at=preorder.detected_at,
                release_date=preorder.release_date,
                confidence=preorder.confidence,
            )
        )
    return out


@router.get("/price-history/{product_id}", response_model=list[PriceHistoryOut])
async def price_history(product_id: int, session: AsyncSession = Depends(get_session)):
    """Serie histórica por tienda para un producto canónico."""
    listings = (
        await session.scalars(
            select(Listing)
            .options(selectinload(Listing.store))
            .where(Listing.canonical_product_id == product_id)
        )
    ).all()
    if not listings:
        raise HTTPException(404, "producto sin listings")

    series = []
    for listing in listings:
        points = (
            await session.scalars(
                select(PriceHistory)
                .where(PriceHistory.listing_id == listing.id)
                .order_by(PriceHistory.recorded_at)
            )
        ).all()
        effective = [p.sale_price or p.price for p in points]
        series.append(
            PriceHistoryOut(
                store_name=listing.store.name,
                listing_id=listing.id,
                points=[PricePointOut.model_validate(p) for p in points],
                min_price=min(effective, default=None),
                max_price=max(effective, default=None),
                avg_price=sum(effective) / len(effective) if effective else None,
            )
        )
    return series
