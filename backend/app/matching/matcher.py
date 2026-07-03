"""Matching de listings contra el catálogo canónico.

Pipeline (ver instrucciones.md):
1. Match exacto por atributos (set + tipo + idioma).
2. Fuzzy matching con umbral alto (>= 92): vincular automáticamente.
3. Score intermedio (85-92): cola de revisión manual.
4. Sin match: crear producto canónico nuevo.

Nunca se cruzan productos de distinto idioma.
"""

from dataclasses import dataclass

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.matching.normalizer import extract
from app.models import CanonicalProduct, Language, Listing, MatchReview, MatchReviewStatus


@dataclass
class MatchResult:
    product: CanonicalProduct | None
    created: bool
    needs_review: bool


async def match_listing(session: AsyncSession, listing: Listing) -> MatchResult:
    settings = get_settings()
    attrs = extract(listing.raw_name)

    if listing.language == Language.UNKNOWN and attrs.language != Language.UNKNOWN:
        listing.language = attrs.language
    language = listing.language

    # Candidatos: mismo idioma siempre; productos de idioma desconocido no se
    # auto-fusionan con nada hasta que se les defina idioma.
    candidates = (
        await session.scalars(
            select(CanonicalProduct).where(CanonicalProduct.language == language)
        )
    ).all()

    # 1. Match exacto por atributos
    if attrs.set_code and attrs.product_type:
        for c in candidates:
            if c.set_code == attrs.set_code and c.product_type == attrs.product_type:
                return MatchResult(product=c, created=False, needs_review=False)

    # 2-3. Fuzzy matching sobre nombre normalizado
    best: CanonicalProduct | None = None
    best_score = 0.0
    for c in candidates:
        score = fuzz.token_sort_ratio(attrs.normalized_name, c.normalized_name)
        if score > best_score:
            best, best_score = c, score

    if best is not None and best_score >= settings.fuzzy_auto_match_threshold:
        return MatchResult(product=best, created=False, needs_review=False)

    if best is not None and best_score >= settings.fuzzy_review_threshold:
        session.add(
            MatchReview(
                listing_id=listing.id,
                candidate_product_id=best.id,
                score=int(best_score),
                status=MatchReviewStatus.PENDING,
            )
        )
        return MatchResult(product=None, created=False, needs_review=True)

    # 4. Crear producto canónico nuevo
    product = CanonicalProduct(
        normalized_name=attrs.normalized_name,
        display_name=listing.raw_name,
        set_code=attrs.set_code,
        product_type=attrs.product_type,
        language=language,
        image_url=listing.image_url,
    )
    session.add(product)
    await session.flush()
    return MatchResult(product=product, created=True, needs_review=False)
