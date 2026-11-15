"""Tabela de unidades v1.1 (planning/04 §4; extensão aditiva DIV-33).

Regras:
- Conversão determinística para SI; o valor original nunca é sobrescrito.
- Temperatura usa DESLOCAMENTO (K = °C + 273,15), não só fator.
- Unidade desconhecida não é convertida "aproximadamente": `normalize` devolve None.
- Grafias passam por normalização Unicode (NFKC + sinais equivalentes: ℃ → °C, º/˚ → °, µ/μ → u,
  espaços NBSP/finos → espaço) ANTES da busca no dicionário de apelidos.
- Esta tabela decide a igualdade FÍSICA; nunca se compara texto de unidade para isso.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import unicodedata

# canônica -> (dimensão, fator para SI, unidade SI, deslocamento) ;  SI = valor*fator + deslocamento
_UNITS: dict[str, tuple[str, float, str, float]] = {
    # comprimento
    "um": ("length", 1e-6, "m", 0.0), "mm": ("length", 1e-3, "m", 0.0), "cm": ("length", 1e-2, "m", 0.0),
    "m": ("length", 1.0, "m", 0.0), "in": ("length", 0.0254, "m", 0.0),
    # velocidade
    "mm/s": ("velocity", 1e-3, "m/s", 0.0), "cm/s": ("velocity", 1e-2, "m/s", 0.0), "m/s": ("velocity", 1.0, "m/s", 0.0),
    # tempo
    "ms": ("time", 1e-3, "s", 0.0), "s": ("time", 1.0, "s", 0.0), "min": ("time", 60.0, "s", 0.0),
    "h": ("time", 3600.0, "s", 0.0),
    # temperatura (absoluta)
    "degC": ("temperature", 1.0, "K", 273.15), "K": ("temperature", 1.0, "K", 0.0),
    "degF": ("temperature", 5.0 / 9.0, "K", 273.15 - 32.0 * 5.0 / 9.0),
    # ângulo
    "deg": ("angle", math.pi / 180.0, "rad", 0.0), "rad": ("angle", 1.0, "rad", 0.0),
    # pressão
    "Pa": ("pressure", 1.0, "Pa", 0.0), "kPa": ("pressure", 1e3, "Pa", 0.0), "MPa": ("pressure", 1e6, "Pa", 0.0),
    "mbar": ("pressure", 1e2, "Pa", 0.0), "bar": ("pressure", 1e5, "Pa", 0.0),
    "atm": ("pressure", 101325.0, "Pa", 0.0), "psi": ("pressure", 6894.757293168, "Pa", 0.0),
    # volume, massa, área
    "mL": ("volume", 1e-6, "m3", 0.0), "L": ("volume", 1e-3, "m3", 0.0), "cm3": ("volume", 1e-6, "m3", 0.0),
    "m3": ("volume", 1.0, "m3", 0.0),
    "mg": ("mass", 1e-6, "kg", 0.0), "g": ("mass", 1e-3, "kg", 0.0), "kg": ("mass", 1.0, "kg", 0.0),
    "mm2": ("area", 1e-6, "m2", 0.0), "cm2": ("area", 1e-4, "m2", 0.0), "m2": ("area", 1.0, "m2", 0.0),
    # frequência, potência, fluxo de calor
    "Hz": ("frequency", 1.0, "Hz", 0.0),
    "W": ("power", 1.0, "W", 0.0), "kW": ("power", 1e3, "W", 0.0), "kW/m2": ("heat_flux", 1e3, "W/m2", 0.0),
    # frações
    "%": ("fraction", 1e-2, "fraction", 0.0), "ppm": ("fraction", 1e-6, "fraction", 0.0),
    "fraction": ("fraction", 1.0, "fraction", 0.0),
    "adimensional": ("dimensionless", 1.0, "adimensional", 0.0),
}

DIMENSION_PT = {
    "length": "comprimento", "velocity": "velocidade", "time": "tempo", "temperature": "temperatura",
    "angle": "ângulo", "pressure": "pressão", "volume": "volume", "mass": "massa", "area": "área",
    "frequency": "frequência", "power": "potência", "heat_flux": "fluxo de calor", "fraction": "fração/percentual",
    "dimensionless": "grandeza sem unidade",
}

DISPLAY = {"um": "µm", "degC": "°C", "degF": "°F", "deg": "°", "cm3": "cm³", "m3": "m³", "mm2": "mm²",
           "cm2": "cm²", "m2": "m²", "kW/m2": "kW/m²", "adimensional": "sem unidade", "fraction": "fração"}

# grafias aceitas (já como seriam normalizadas) -> unidade canônica
_RAW_ALIASES: dict[str, str] = {
    "um": "um", "micrometer": "um", "micrometers": "um", "micrometro": "um", "micrometros": "um", "micron": "um",
    "mm": "mm", "milímetro": "mm", "milímetros": "mm", "milimetro": "mm", "milimetros": "mm", "millimeter": "mm", "millimeters": "mm",
    "cm": "cm", "centímetro": "cm", "centímetros": "cm", "centimetro": "cm", "centimetros": "cm", "centimeter": "cm", "centimeters": "cm",
    "m": "m", "metro": "m", "metros": "m", "meter": "m", "meters": "m", "in": "in", "inch": "in", "inches": "in", "polegada": "in",
    "mm/s": "mm/s", "mm s-1": "mm/s", "mm·s-1": "mm/s", "cm/s": "cm/s", "cm s-1": "cm/s", "cm·s-1": "cm/s",
    "m/s": "m/s", "m s-1": "m/s", "m·s-1": "m/s",
    "ms": "ms", "millisecond": "ms", "milliseconds": "ms", "milissegundo": "ms", "milissegundos": "ms",
    "s": "s", "seg": "s", "segundo": "s", "segundos": "s", "second": "s", "seconds": "s", "sec": "s",
    "min": "min", "minuto": "min", "minutos": "min", "minute": "min", "minutes": "min",
    "h": "h", "hr": "h", "hora": "h", "horas": "h", "hour": "h", "hours": "h",
    "°c": "degC", "degc": "degC", "deg c": "degC", "degree c": "degC", "degrees c": "degC", "degree celsius": "degC",
    "degrees celsius": "degC", "celsius": "degC", "grau celsius": "degC", "graus celsius": "degC", "grau c": "degC", "graus c": "degC",
    "k": "K", "kelvin": "K", "kelvins": "K",
    "°f": "degF", "degf": "degF", "deg f": "degF", "degrees f": "degF", "fahrenheit": "degF",
    "°": "deg", "deg": "deg", "degree": "deg", "degrees": "deg", "grau": "deg", "graus": "deg", "rad": "rad", "radian": "rad", "radians": "rad",
    "pa": "Pa", "pascal": "Pa", "kpa": "kPa", "mpa": "MPa", "mbar": "mbar", "bar": "bar", "atm": "atm", "psi": "psi",
    "ml": "mL", "l": "L", "liter": "L", "litre": "L", "litro": "L", "litros": "L", "cm3": "cm3", "cc": "cm3", "m3": "m3",
    "mg": "mg", "g": "g", "kg": "kg", "mm2": "mm2", "cm2": "cm2", "m2": "m2",
    "hz": "Hz", "w": "W", "kw": "kW", "kw/m2": "kW/m2",
    "%": "%", "% vol": "%", "% vol.": "%", "%vol": "%", "vol%": "%", "vol.%": "%", "vol %": "%", "vol. %": "%",
    "por cento": "%", "percent": "%", "ppm": "ppm",
    "fraction": "fraction", "fração": "fraction", "fracao": "fraction",
    "adimensional": "adimensional", "dimensionless": "adimensional", "none": "adimensional", "n/a": "adimensional",
    "na": "adimensional", "-": "adimensional", "—": "adimensional", "–": "adimensional", "1": "adimensional", "": "adimensional",
    "sem unidade": "adimensional",
}

_TRANSLATE = str.maketrans({"º": "°", "˚": "°", "∘": "°", "µ": "u", "μ": "u", "−": "-", " ": " ", " ": " ",
                            " ": " ", " ": " ", " ": " ", "​": ""})


def pre_normalize(text: str) -> str:
    """Normalização Unicode segura para texto científico: ANTES do NFKC troca º/˚/µ por equivalentes
    (o NFKC transformaria º em "o"); depois NFKC (℃ → °C, ² → 2, K Kelvin → K)."""
    s = text.translate(_TRANSLATE)
    s = unicodedata.normalize("NFKC", s)
    return s.translate(_TRANSLATE)


def unit_key(text: str | None) -> str:
    """Normaliza a grafia de uma unidade (Unicode, espaços, caixa) para busca nos apelidos."""
    if text is None:
        return ""
    s = pre_normalize(text).strip().strip(".").lower()
    s = " ".join(s.split())
    return s.replace("° ", "°") if s[:1] == "°" and len(s) > 2 and s[2:3] != "" else s


_ALIASES: dict[str, str] = {unit_key(k): v for k, v in _RAW_ALIASES.items()}


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
    return _ALIASES.get(unit_key(unit))


def is_known_unit(unit: str | None) -> bool:
    return canonical_unit(unit) is not None


def display_unit(canon: str | None) -> str:
    return DISPLAY.get(canon or "", canon or "")


def dimension_of(canon: str | None) -> str | None:
    return _UNITS[canon][0] if canon in _UNITS else None


def normalize(value: float, unit: str | None) -> Quantity | None:
    """Converte para SI (com deslocamento quando houver). Devolve None para unidade desconhecida."""
    canon = canonical_unit(unit)
    if canon is None:
        return None
    dimension, factor, si_unit, offset = _UNITS[canon]
    return Quantity(value=value * factor + offset, unit=si_unit, dimension=dimension)


def same_quantity(a: Quantity, b: Quantity, rel_tol: float = 1e-6, abs_tol: float = 1e-12) -> bool:
    return a.dimension == b.dimension and math.isclose(a.value, b.value, rel_tol=rel_tol, abs_tol=abs_tol)
