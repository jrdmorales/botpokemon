import pytest

from app.scraping.price_parser import PriceParseError, parse_clp, validate_pair


class TestParseClp:
    def test_formato_chileno_punto_miles(self):
        assert parse_clp("$45.990") == 45990

    def test_formato_chileno_millon(self):
        assert parse_clp("$1.299.990") == 1299990

    def test_sin_simbolo(self):
        assert parse_clp("45.990") == 45990

    def test_con_texto_alrededor(self):
        assert parse_clp("Precio: $12.500 CLP") == 12500

    def test_entero_directo(self):
        assert parse_clp(45990) == 45990

    def test_float_directo(self):
        assert parse_clp(45990.0) == 45990

    def test_decimal_extranjero_se_descarta(self):
        # "45990.00" — punto seguido de exactamente 2 decimales en número largo
        assert parse_clp("45990.00") == 45990

    def test_coma_como_separador_miles(self):
        assert parse_clp("45,990") == 45990

    def test_precio_vacio(self):
        with pytest.raises(PriceParseError):
            parse_clp(None)

    def test_sin_digitos(self):
        with pytest.raises(PriceParseError):
            parse_clp("Consultar")

    def test_precio_cero_rechazado(self):
        with pytest.raises(PriceParseError):
            parse_clp("0")

    def test_precio_absurdo_rechazado(self):
        with pytest.raises(PriceParseError):
            parse_clp("$99.999.999")

    def test_tope_por_categoria(self):
        # Booster pack a 150.000 CLP: error de parsing casi seguro
        with pytest.raises(PriceParseError):
            parse_clp("$150.000", max_sane_price=20000)

    def test_dentro_del_tope(self):
        assert parse_clp("$5.990", max_sane_price=20000) == 5990


class TestValidatePair:
    def test_oferta_menor_ok(self):
        assert validate_pair(45990, 39990) is True

    def test_sin_oferta_ok(self):
        assert validate_pair(45990, None) is True

    def test_oferta_mayor_sospechoso(self):
        assert validate_pair(39990, 45990) is False
