"""Tabela de unidades v1 (planning/04 §4) — implementação mínima para o verificador V2.

Escopo: somente o necessário para BL-05.03. A consolidação completa (validação de
registros no carregamento do dataset) pertence a BL-02.02/BL-02.03.

Regras:
- Conversão determinística para SI; o valor original nunca é sobrescrito.
- Unidade desconhecida não é convertida "aproximadamente": `normalize` devolve None.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

# unidade canônica -> (dimensão, fator para SI, unidade SI)
_UNITS: dict[str, tuple[str, float, str]] = {
    "mm": ("length", 1e-3, "m"),
    "cm": ("length", 1e-2, "m"),
    "m": ("length", 1.0, "m"),
    "mm/s": ("velocity", 1e-3, "m/s"),
    "cm/s": ("velocity", 1e-2, "m/s"),
    "m/s": ("velocity", 1.0, "m/s"),
    "s": ("time", 1.0, "s"),
    "min": ("time", 60.0, "s"),
    "%": ("fraction", 1e-2, "fraction"),
    "fraction": ("fraction", 1.0, "fraction"),
    "adimensional": ("dimensionless", 1.0, "adimensional"),
}

# grafias aceitas -> unidade canônica (comparação em minúsculas)
_ALIASES: dict[str, str] = {
    "mm": "mm", "milímetro": "mm", "milímetros": "mm", "milimetro": "mm", "milimetros": "mm",
    "millimeter": "mm", "millimeters": "mm",
    "cm": "cm", "centímetro": "cm", "centímetros": "cm", "centimetro": "cm", "centimetros": "cm",
    "centimeter": "cm", "centimeters": "cm",
    "m": "m", "metro": "m", "metros": "m", "meter": "m", "meters": "m",
    "mm/s": "mm/s", "mm s-1": "mm/s", "mm·s⁻¹": "mm/s", "mm s⁻¹": "mm/s",
    "cm/s": "cm/s", "cm s-1": "cm/s", "cm·s⁻¹": "cm/s", "cm s⁻¹": "cm/s",
    "m/s": "m/s", "m s-1": "m/s", "m·s⁻¹": "m/s", "m s⁻¹": "m/s",
    "s": "s", "seg": "s", "segundo": "s", "segundos": "s", "second": "s", "seconds": "s", "sec": "s",
    "min": "min", "minuto": "min", "minutos": "min", "minute": "min", "minutes": "min",
    "%": "%", "% vol": "%", "% vol.": "%", "%vol": "%", "por cento": "%", "percent": "%",
    "fraction": "fraction", "fração": "fraction", "fracao": "fraction",
    "adimensional": "adimensional", "dimensionless": "adimensional", "": "adimensional",
}


@dataclass(frozen=True)
class Quantity:
    """Grandeza normalizada em SI."""

    value: float
    unit: str  # unidade SI
    dimension: str


def canonical_unit(unit: str | None) -> str | None:
    """Unidade canônica conhecida, ou None se desconhecida. `None` → adimensional."""
    if unit is None:
        return "adimensional"
    key = " ".join(unit.strip().lower().split())
    return _ALIASES.get(key)


def is_known_unit(unit: str | None) -> bool:
    return canonical_unit(unit) is not None


def normalize(value: float, unit: str | None) -> Quantity | None:
    """Converte para SI. Devolve None para unidade desconhecida (nunca aproxima)."""
    canon = canonical_unit(unit)
    if canon is None:
        return None
    dimension, factor, si_unit = _UNITS[canon]
    return Quantity(value=value * factor, unit=si_unit, dimension=dimension)


def same_quantity(a: Quantity, b: Quantity, rel_tol: float = 1e-6, abs_tol: float = 1e-12) -> bool:
    return a.dimension == b.dimension and math.isclose(a.value, b.value, rel_tol=rel_tol, abs_tol=abs_tol)
