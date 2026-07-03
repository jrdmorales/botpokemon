"""Detección de preventas por keywords — capa de RESPALDO, confianza baja.

La señal confiable es la detección estructurada (preventa_marker en la config
de cada tienda). Lo detectado solo por keywords pasa por revisión antes de
generar alertas públicas.
"""

import re

from app.matching.normalizer import strip_accents

_PREORDER_RE = re.compile(r"\b(preventa|pre-venta|preorder|pre-order|reserva)\b")

_RELEASE_DATE_RE = re.compile(
    r"(?:lanzamiento|disponible|llega|release)[^\d]{0,30}(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})"
)


def looks_like_preorder(text: str) -> bool:
    return bool(_PREORDER_RE.search(strip_accents(text.lower())))


def extract_release_date(text: str) -> tuple[int, int, int] | None:
    """Devuelve (día, mes, año) si encuentra fecha de lanzamiento en el texto."""
    match = _RELEASE_DATE_RE.search(strip_accents(text.lower()))
    if not match:
        return None
    day, month, year = (int(g) for g in match.groups())
    if year < 100:
        year += 2000
    if not (1 <= day <= 31 and 1 <= month <= 12):
        return None
    return day, month, year
