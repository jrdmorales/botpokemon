"""Normalización de nombres de producto y extracción de atributos.

Convierte el nombre crudo de la tienda en (nombre_normalizado, set, tipo, idioma)
para el matching contra el catálogo canónico.
"""

import re
import unicodedata
from dataclasses import dataclass

from app.models import Language

# Abreviaciones comunes en tiendas chilenas → forma canónica
_ABBREVIATIONS: dict[str, str] = {
    r"\betb\b": "elite trainer box",
    r"\bsv\b": "scarlet violet",
    r"\bs&v\b": "scarlet violet",
    r"\bescarlata y purpura\b": "scarlet violet",
    r"\bescarlata & purpura\b": "scarlet violet",
    r"\bbb\b": "booster box",
    r"\bdisplay\b": "booster box",
    r"\bsobre\b": "booster pack",
    r"\bsobres\b": "booster pack",
    r"\bcaja de entrenador elite\b": "elite trainer box",
    r"\bbundle de 6 sobres\b": "booster bundle",
}

# Sets conocidos de Pokémon TCG (nombre normalizado → código). Mantener actualizado.
SETS: dict[str, str] = {
    "scarlet violet 151": "sv3pt5",
    "151": "sv3pt5",
    "obsidian flames": "sv3",
    "llamas obsidianas": "sv3",
    "paldea evolved": "sv2",
    "evoluciones en paldea": "sv2",
    "scarlet violet base": "sv1",
    "paradox rift": "sv4",
    "paraje paradojico": "sv4",
    "paldean fates": "sv4pt5",
    "destinos de paldea": "sv4pt5",
    "temporal forces": "sv5",
    "fuerzas temporales": "sv5",
    "twilight masquerade": "sv6",
    "mascarada crepuscular": "sv6",
    "shrouded fable": "sv6pt5",
    "stellar crown": "sv7",
    "corona astral": "sv7",
    "surging sparks": "sv8",
    "chispas fulgurantes": "sv8",
    "prismatic evolutions": "sv8pt5",
    "evoluciones prismaticas": "sv8pt5",
}

PRODUCT_TYPES: list[str] = [
    "elite trainer box",
    "booster box",
    "booster bundle",
    "booster pack",
    "collection box",
    "premium collection",
    "bundle",
    "tin",
    "blister",
]

_ES_MARKERS = re.compile(r"\b(espanol|español|spanish|esp)\b")
_EN_MARKERS = re.compile(r"\b(ingles|english|eng)\b")


@dataclass(frozen=True)
class NormalizedProduct:
    normalized_name: str
    set_code: str | None
    product_type: str | None
    language: Language


def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )


def normalize_name(raw: str) -> str:
    text = strip_accents(raw.lower())
    text = re.sub(r"[^\w\s&]", " ", text)
    for pattern, replacement in _ABBREVIATIONS.items():
        text = re.sub(pattern, replacement, text)
    text = re.sub(r"\bpokemon\b|\btcg\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def detect_language(raw: str) -> Language:
    text = strip_accents(raw.lower())
    if _ES_MARKERS.search(text):
        return Language.ES
    if _EN_MARKERS.search(text):
        return Language.EN
    return Language.UNKNOWN


def extract(raw_name: str) -> NormalizedProduct:
    normalized = normalize_name(raw_name)

    set_code = None
    # Buscar primero los nombres de set más largos para evitar que "151" gane sobre
    # "scarlet violet 151"
    for set_name in sorted(SETS, key=len, reverse=True):
        if set_name in normalized:
            set_code = SETS[set_name]
            break

    product_type = None
    for ptype in PRODUCT_TYPES:  # ordenados de más específico a más genérico
        if ptype in normalized:
            product_type = ptype
            break

    return NormalizedProduct(
        normalized_name=normalized,
        set_code=set_code,
        product_type=product_type,
        language=detect_language(raw_name),
    )
