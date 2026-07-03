from app.matching.normalizer import detect_language, extract, normalize_name
from app.models import Language


class TestNormalizeName:
    def test_expande_etb(self):
        assert "elite trainer box" in normalize_name("ETB Scarlet & Violet 151")

    def test_quita_tildes_y_pokemon(self):
        normalized = normalize_name("Caja Pokémon Evoluciones en Paldea")
        assert "pokemon" not in normalized
        assert "evoluciones en paldea" in normalized

    def test_sobres_a_booster_pack(self):
        assert "booster pack" in normalize_name("Sobres Pokémon TCG 151")


class TestDetectLanguage:
    def test_espanol(self):
        assert detect_language("ETB 151 Español") == Language.ES

    def test_ingles(self):
        assert detect_language("ETB 151 (Inglés)") == Language.EN

    def test_english_marker(self):
        assert detect_language("Booster Box Surging Sparks ENGLISH") == Language.EN

    def test_desconocido(self):
        assert detect_language("ETB Paradox Rift") == Language.UNKNOWN


class TestExtract:
    def test_etb_151(self):
        result = extract("ETB Pokémon Scarlet & Violet 151 Inglés")
        assert result.set_code == "sv3pt5"
        assert result.product_type == "elite trainer box"
        assert result.language == Language.EN

    def test_set_es_y_en_mismo_codigo(self):
        en = extract("Booster Box Surging Sparks")
        es = extract("Display Chispas Fulgurantes Español")
        assert en.set_code == es.set_code == "sv8"

    def test_set_largo_gana_sobre_corto(self):
        # "scarlet violet 151" debe ganar sobre el set "151" a secas
        result = extract("Elite Trainer Box Scarlet & Violet 151")
        assert result.set_code == "sv3pt5"

    def test_mismo_producto_distintas_tiendas(self):
        """Caso real del comparador: dos nombres distintos, mismos atributos."""
        a = extract("ETB Scarlet & Violet 151 (Inglés)")
        b = extract("Pokémon TCG: Elite Trainer Box SV 151 English")
        assert a.set_code == b.set_code
        assert a.product_type == b.product_type
        assert a.language == b.language
