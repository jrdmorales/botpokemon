"""Endpoints de administración (API key requerida)."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import MatchReviewOut
from app.config import get_settings
from app.db import get_session
from app.models import (
    CanonicalProduct,
    Listing,
    MatchReview,
    MatchReviewStatus,
    ScraperRun,
    Store,
)


def require_admin(x_api_key: str = Header()) -> None:
    if x_api_key != get_settings().admin_api_key:
        raise HTTPException(401, "API key inválida")


router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])


@router.get("/match-queue", response_model=list[MatchReviewOut])
async def match_queue(session: AsyncSession = Depends(get_session)):
    reviews = (
        await session.scalars(
            select(MatchReview).where(MatchReview.status == MatchReviewStatus.PENDING)
        )
    ).all()
    out = []
    for review in reviews:
        listing = await session.get(Listing, review.listing_id)
        candidate = await session.get(CanonicalProduct, review.candidate_product_id)
        out.append(
            MatchReviewOut(
                id=review.id,
                listing_id=review.listing_id,
                listing_name=listing.raw_name if listing else "?",
                candidate_product_id=review.candidate_product_id,
                candidate_name=candidate.display_name if candidate else "?",
                score=review.score,
                status=review.status,
            )
        )
    return out


@router.post("/match-queue/{review_id}/approve")
async def approve_match(review_id: int, session: AsyncSession = Depends(get_session)):
    review = await session.get(MatchReview, review_id)
    if review is None or review.status != MatchReviewStatus.PENDING:
        raise HTTPException(404, "revisión no encontrada o ya resuelta")
    listing = await session.get(Listing, review.listing_id)
    if listing is None:
        raise HTTPException(404, "listing no existe")
    listing.canonical_product_id = review.candidate_product_id
    review.status = MatchReviewStatus.APPROVED
    review.resolved_at = datetime.now(UTC)
    await session.commit()
    return {"ok": True}


@router.post("/match-queue/{review_id}/reject")
async def reject_match(review_id: int, session: AsyncSession = Depends(get_session)):
    review = await session.get(MatchReview, review_id)
    if review is None or review.status != MatchReviewStatus.PENDING:
        raise HTTPException(404, "revisión no encontrada o ya resuelta")
    review.status = MatchReviewStatus.REJECTED
    review.resolved_at = datetime.now(UTC)
    await session.commit()
    return {"ok": True}


@router.get("/scraper-health")
async def scraper_health(session: AsyncSession = Depends(get_session)):
    stores = (await session.scalars(select(Store))).all()
    out = []
    for store in stores:
        last_run = await session.scalar(
            select(ScraperRun)
            .where(ScraperRun.store_id == store.id)
            .order_by(ScraperRun.started_at.desc())
            .limit(1)
        )
        out.append(
            {
                "store": store.slug,
                "last_successful_scrape": store.last_successful_scrape,
                "last_run": {
                    "started_at": last_run.started_at,
                    "success": last_run.success,
                    "products_found": last_run.products_found,
                    "errors": last_run.errors,
                }
                if last_run
                else None,
            }
        )
    return out
