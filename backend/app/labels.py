"""Nome amigável em português para parâmetros extraídos (snake_case em inglês).

Tradução determinística por glossário (sem IA, sem inventar): palavras desconhecidas ficam como estão.
Adjetivos vão para depois do substantivo ("initial_temperature" → "Temperatura inicial") e concordam
em gênero com o substantivo principal quando há forma própria.
"""

from __future__ import annotations

import re

_NOUNS = {  # termo → (português, feminino?)
    "temperature": ("temperatura", True), "pressure": ("pressão", True), "width": ("largura", True),
    "length": ("comprimento", False), "thickness": ("espessura", True), "diameter": ("diâmetro", False),
    "radius": ("raio", False), "angle": ("ângulo", False), "velocity": ("velocidade", True), "speed": ("velocidade", True),
    "rate": ("taxa", True), "time": ("tempo", False), "duration": ("duração", True), "density": ("densidade", True),
    "viscosity": ("viscosidade", True), "tension": ("tensão", True), "concentration": ("concentração", True),
    "accuracy": ("precisão", True), "uncertainty": ("incerteza", True), "increment": ("incremento", False),
    "date": ("data", True), "mass": ("massa", True), "volume": ("volume", False), "flux": ("fluxo", False),
    "power": ("potência", True), "code": ("código", False), "material": ("material", False), "fluid": ("fluido", False),
    "liquid": ("líquido", False), "solid": ("sólido", False), "modifier": ("modificador", False), "surface": ("superfície", True),
    "cell": ("célula", True), "cells": ("células", True), "sample": ("amostra", True), "oxygen": ("oxigênio", False),
    "flame": ("chama", True), "spread": ("propagação", True), "heat": ("calor", False), "flow": ("escoamento", False),
    "humidity": ("umidade", True), "gravity": ("gravidade", True), "geometry": ("geometria", True), "duct": ("duto", False),
    "holder": ("suporte", False), "report": ("relatório", False), "test": ("ensaio", False), "angles": ("ângulos", False),
    "index": ("índice", False), "refraction": ("refração", True), "wavelength": ("comprimento de onda", False),
    "contact": ("contato", False),
    "fill": ("preenchimento", False), "airflow": ("fluxo de ar", False), "port": ("porta", True), "ports": ("portas", True), "number": ("número", False),
}
_ADJ = {  # termo → (masculino, feminino)
    "initial": ("inicial", "inicial"), "final": ("final", "final"), "peak": ("de pico", "de pico"),
    "planned": ("planejado", "planejada"), "achieved": ("alcançado", "alcançada"), "maximum": ("máximo", "máxima"),
    "max": ("máximo", "máxima"), "minimum": ("mínimo", "mínima"), "min": ("mínimo", "mínima"),
    "average": ("médio", "média"), "mean": ("médio", "média"), "measured": ("medido", "medida"),
    "estimated": ("estimado", "estimada"), "nominal": ("nominal", "nominal"), "uncoated": ("sem revestimento", "sem revestimento"),
    "coated": ("revestido", "revestida"), "equilibrium": ("de equilíbrio", "de equilíbrio"), "dihedral": ("diedral", "diedral"),
    "ambient": ("ambiente", "ambiente"), "total": ("total", "total"), "start": ("inicial", "inicial"),
    "lower": ("inferior", "inferior"), "upper": ("superior", "superior"),
}

def friendly_label(slug: str | None) -> str:
    """"initial_temperature" → "Temperatura inicial"; "contact_angle_accuracy" → "Precisão de ângulo de contato";
    "peak_temperature_planned" → "Temperatura de pico planejada". Composto em inglês (modificador → núcleo)
    vira núcleo + "de" + modificadores em ordem inversa; adjetivos concordam com o gênero do núcleo."""
    words = [w for w in re.split(r"[_\s]+", (slug or "").strip().lower()) if w]
    if not words:
        return ""
    nouns: list[tuple[str, bool]] = []
    adjs: list[str] = []
    others: list[str] = []
    for w in words:
        if w in _NOUNS:
            nouns.append(_NOUNS[w])
        elif w in _ADJ:
            adjs.append(w)
        else:
            others.append(w)
    if nouns:
        head, feminine = nouns[-1]
        modifiers = [n for n, _ in reversed(nouns[:-1])]
        core = " de ".join([head] + modifiers)
    else:
        core, feminine = "", False
    qualifiers = [(_ADJ[a][1] if feminine else _ADJ[a][0]) for a in adjs]
    text = " ".join(x for x in [core, *qualifiers, *others] if x).strip()
    return text[:1].upper() + text[1:] if text else ""
