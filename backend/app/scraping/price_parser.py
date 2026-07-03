"""Parser de precios chilenos.

Reglas críticas (ver instrucciones.md):
- El punto es separador de miles ("$45.990" = 45990 CLP), NUNCA decimal.
- CLP no usa decimales: almacenar como entero.
- Rechazar valores absurdos según tope por categoría.
"""

import re

DEFAULT_MAX_SANE_PRICE = 2_000_000  # CLP; tope global si la categoría no define uno
MIN_SANE_PRICE = 100


class PriceParseError(ValueError):
    pass


_PRICE_RE = re.compile(r"(\d[\d.,\s]*\d|\d)")


def parse_clp(raw: str | int | float | None, max_sane_price: int | None = None) -> int:
    """Convierte un precio crudo a entero CLP. Lanza PriceParseError si es inválido."""
    if raw is None:
        raise PriceParseError("precio vacío")

    if isinstance(raw, (int, float)):
        value = int(raw)
    else:
        match = _PRICE_RE.search(raw)
        if not match:
            raise PriceParseError(f"sin dígitos en {raw!r}")
        digits = match.group(1)
        # Coma o punto seguidos de exactamente 2 dígitos al final: formato decimal
        # extranjero ("45990.00") — descartar los decimales. En todo otro caso,
        # punto/coma/espacio son separadores de miles.
        decimal = re.search(r"[.,](\d{2})$", digits)
        if decimal and not re.fullmatch(r"\d{1,3}[.,]\d{2}", digits):
            digits = digits[: decimal.start()]
        elif decimal and len(digits) <= 6:
            # "45.99" ambiguo: en contexto chileno un precio de 2 dígitos no existe,
            # tratamos punto como separador de miles ("45.990" ya no matchea aquí).
            pass
        value = int(re.sub(r"[.,\s]", "", digits))

    upper = max_sane_price or DEFAULT_MAX_SANE_PRICE
    if value < MIN_SANE_PRICE:
        raise PriceParseError(f"precio {value} bajo el mínimo razonable ({MIN_SANE_PRICE} CLP)")
    if value > upper:
        raise PriceParseError(f"precio {value} sobre el tope razonable ({upper} CLP)")
    return value


def validate_pair(price: int, sale_price: int | None) -> bool:
    """True si el par precio/oferta es coherente. Oferta mayor al normal = sospechoso."""
    if sale_price is None:
        return True
    return sale_price <= price
