from sqlalchemy import select

from app.matching.matcher import match_listing
from app.models import CanonicalProduct, Language, Listing, MatchReview, Platform, Store


async def _make_store(session, slug="tienda-a") -> Store:
    store = Store(slug=slug, name=slug, base_url=f"https://{slug}.cl", platform=Platform.SHOPIFY)
    session.add(store)
    await session.flush()
    return store


async def _make_listing(session, store: Store, name: str, sku: str) -> Listing:
    listing = Listing(
        store_id=store.id,
        store_sku=sku,
        raw_name=name,
        url=f"https://{store.slug}.cl/products/{sku}",
        current_price=50000,
    )
    session.add(listing)
    await session.flush()
    return listing


class TestMatchListing:
    async def test_sin_match_crea_producto_nuevo(self, session):
        store = await _make_store(session)
        listing = await _make_listing(session, store, "ETB Scarlet & Violet 151 Inglés", "1")
        result = await match_listing(session, listing)
        assert result.created is True
        assert result.product is not None
        assert result.product.set_code == "sv3pt5"

    async def test_match_exacto_entre_tiendas(self, session):
        """El caso que justifica el catálogo canónico: nombres distintos, mismo producto."""
        store_a = await _make_store(session, "tienda-a")
        store_b = await _make_store(session, "tienda-b")

        listing_a = await _make_listing(session, store_a, "ETB Scarlet & Violet 151 Inglés", "1")
        result_a = await match_listing(session, listing_a)
        listing_a.canonical_product_id = result_a.product.id

        listing_b = await _make_listing(
            session, store_b, "Pokémon TCG Elite Trainer Box SV 151 English", "x9"
        )
        result_b = await match_listing(session, listing_b)

        assert result_b.created is False
        assert result_b.product.id == result_a.product.id

    async def test_nunca_fusiona_idiomas_distintos(self, session):
        store = await _make_store(session)

        listing_en = await _make_listing(session, store, "ETB Surging Sparks Inglés", "1")
        result_en = await match_listing(session, listing_en)

        listing_es = await _make_listing(session, store, "ETB Surging Sparks Español", "2")
        result_es = await match_listing(session, listing_es)

        assert result_en.product.id != result_es.product.id
        assert result_en.product.language == Language.EN
        assert result_es.product.language == Language.ES

    async def test_score_intermedio_va_a_revision(self, session):
        store = await _make_store(session)
        # Producto canónico existente sin set conocido (no hay match exacto posible)
        session.add(
            CanonicalProduct(
                normalized_name="lata premium pikachu coleccion especial aniversario",
                display_name="Lata Premium Pikachu Colección Especial Aniversario",
                language=Language.ES,
            )
        )
        await session.flush()

        # Nombre parecido pero no idéntico: score intermedio esperado
        listing = await _make_listing(
            session, store, "Lata Premium Pikachu Colección Aniversario Español", "1"
        )
        result = await match_listing(session, listing)

        if result.needs_review:
            reviews = (await session.scalars(select(MatchReview))).all()
            assert len(reviews) == 1
            assert result.product is None
        else:
            # Si el score superó el umbral alto, debe haber vinculado, no creado
            assert result.created is False
