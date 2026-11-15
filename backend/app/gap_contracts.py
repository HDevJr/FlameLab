"""BL-17.2 — contratos de dados tipados para as lacunas científicas.

Um contrato descreve a ESTRUTURA de uma informação (campos, dimensões físicas, unidades, limites
físicos inequívocos) para que uma proposta seja registrada de forma verificável. Ele NÃO é um
modelo físico validado: nenhum contrato aqui transforma dados em entrada FDS. Essa decisão
pertence ao perfil físico (implementado + aprovado) e à revisão independente.

Regras:
- O valor/unidade enviados são preservados; o SI é registrado separadamente (`units.normalize`).
- Unidade desconhecida ou de dimensão errada é recusada; nada é convertido "aproximadamente".
- Limites aplicados são apenas os fisicamente necessários (comprimento > 0, T > 0 K, ...). Domínios
  de uso pertencem ao perfil físico e não são inventados aqui.
- Nenhuma propriedade de material é presumida a partir do nome do material.
"""
from __future__ import annotations

import copy
import math
import re
import unicodedata
from typing import Any

from backend.app import units

CONTRACT_VERSION = "1.0.0"
KIND_PT = {"QUANTITY": "Grandeza física", "GEOMETRY": "Geometria", "MATERIAL": "Material",
           "PROCEDURE": "Procedimento físico", "MEASUREMENT": "Método de medição", "DOCUMENT": "Registro documental"}

AXES = [(v, v) for v in ("+x", "-x", "+y", "-y", "+z", "-z")]


# ------------------------------------------------------------------ construtores de campos
def qty(name, label, dimension, *, required=True, minimum=None, maximum=None, min_exclusive=True, help=None, when=None):
    return {"name": name, "type": "quantity", "label_pt": label, "dimension": dimension, "required": required,
            "min": minimum, "max": maximum, "min_exclusive": min_exclusive, "help_pt": help, "when": when}


def enum(name, label, options, *, required=True, help=None, when=None):
    return {"name": name, "type": "enum", "label_pt": label, "required": required, "help_pt": help, "when": when,
            "options": [{"value": v, "label_pt": t, **extra} for v, t, *rest in options for extra in [rest[0] if rest else {}]]}


def text(name, label, *, required=True, minimum=2, maximum=2000, multiline=False, help=None, when=None):
    return {"name": name, "type": "text", "label_pt": label, "required": required, "min": minimum, "max": maximum,
            "multiline": multiline, "help_pt": help, "when": when}


def vector(name, label, dimension="length", *, required=True, help=None, when=None):
    return {"name": name, "type": "vector", "label_pt": label, "dimension": dimension, "axes": ["x", "y", "z"],
            "required": required, "help_pt": help, "when": when}


def rows(name, label, columns, *, required=True, min_rows=1, max_rows=30, unique_by=None, increasing=None, help=None, when=None):
    return {"name": name, "type": "rows", "label_pt": label, "columns": columns, "required": required,
            "min_rows": min_rows if required else 0, "max_rows": max_rows, "unique_by": unique_by,
            "increasing": increasing, "help_pt": help, "when": when}


def when(field, *values):
    return {"field": field, "in": list(values)}


# ------------------------------------------------------------------ propriedades de material
# Nomes e dimensões das propriedades que um modelo de material pode exigir. NÃO há valores aqui.
PROPERTIES = [
    ("density", "Densidade", {"dimension": "density"}),
    ("specific_heat", "Calor específico", {"dimension": "specific_heat"}),
    ("thermal_conductivity", "Condutividade térmica", {"dimension": "thermal_conductivity"}),
    ("emissivity", "Emissividade", {"dimension": "fraction"}),
    ("absorption_coefficient", "Coeficiente de absorção", {"dimension": "attenuation"}),
    ("heat_of_reaction", "Calor de pirólise / reação", {"dimension": "specific_energy"}),
    ("pre_exponential_factor", "Fator pré-exponencial (A)", {"dimension": "rate"}),
    ("activation_energy", "Energia de ativação (E)", {"dimension": "molar_energy"}),
    ("reaction_order", "Ordem de reação", {"dimension": "dimensionless"}),
    ("heat_of_combustion", "Calor de combustão", {"dimension": "specific_energy"}),
    ("residue_yield", "Fração de resíduo", {"dimension": "fraction"}),
]
THERMAL_PROPERTIES = [p for p in PROPERTIES if p[0] in {"density", "specific_heat", "thermal_conductivity", "emissivity"}]
# Conjunto mínimo de propriedades para cada estrutura de modelo de material. É uma lista de NOMES
# (o que o modelo precisaria), não uma definição validada do material.
MODEL_REQUIRED = {
    "single_step_arrhenius": ["density", "specific_heat", "thermal_conductivity", "emissivity", "absorption_coefficient",
                              "heat_of_reaction", "pre_exponential_factor", "activation_energy", "reaction_order"],
    "inert_thermal": ["density", "specific_heat", "thermal_conductivity", "emissivity"],
}
PROPERTY_LABEL = {k: t for k, t, _ in PROPERTIES}


def property_rows(name, label, options, *, required=True, help=None):
    return rows(name, label, [
        enum("property", "Propriedade", options),
        qty("value", "Valor", None, minimum=0, min_exclusive=False) | {"dimension_from": "property"},
        text("source", "Fonte desta propriedade", minimum=5, maximum=600),
        text("validity", "Condições de validade (faixa de temperatura, estado, método)", minimum=3, maximum=600),
    ], required=required, unique_by="property", max_rows=len(options), help=help)


# ------------------------------------------------------------------ contratos
def _c(parameter, kind, title, fields, *, validation, development, hypothesis="ALLOWED", intro=None, primary=None):
    return {"parameter": parameter, "kind": kind, "kind_pt": KIND_PT[kind], "title_pt": title, "version": CONTRACT_VERSION,
            "fields": fields, "physical_validation": validation, "hypothesis": hypothesis,
            "development_needed_pt": development, "intro_pt": intro, "primary": primary}


SHAPE_PLATE = [("flat_plate", "Placa plana"), ("rectangular_block", "Bloco retangular"), ("other", "Outra forma (descrever)")]

CONTRACTS: dict[str, dict[str, Any]] = {
    "sample_length": _c("sample_length", "QUANTITY", "Comprimento da amostra",
        [qty("quantity", "Comprimento da amostra", "length", minimum=0, help="Comprimento na direção de propagação.")],
        validation="DATA_CONTRACT_AND_DOMAIN_CHECKS", primary="quantity",
        development=["Gerador do perfil PMMA que use o comprimento para posicionar a amostra na malha (não implementado)."]),
    "ambient_pressure": _c("ambient_pressure", "QUANTITY", "Pressão ambiente",
        [qty("quantity", "Pressão ambiente", "pressure", minimum=0)],
        validation="DATA_CONTRACT_AND_DOMAIN_CHECKS", primary="quantity",
        development=["Gerador do perfil PMMA que aplique a pressão de fundo (não implementado)."]),
    "ambient_temperature": _c("ambient_temperature", "QUANTITY", "Temperatura ambiente",
        [qty("quantity", "Temperatura ambiente", "temperature", minimum=0, help="Temperatura absoluta deve ser > 0 K.")],
        validation="DATA_CONTRACT_AND_DOMAIN_CHECKS", primary="quantity",
        development=["Gerador do perfil PMMA que aplique a temperatura inicial do gás e da amostra (não implementado)."]),
    "sample_holder_substrate": _c("sample_holder_substrate", "GEOMETRY", "Suporte / substrato da amostra", [
        enum("shape", "Forma geométrica do suporte", SHAPE_PLATE),
        text("shape_description", "Descrição da forma", minimum=10, when=when("shape", "other")),
        qty("length", "Comprimento do suporte", "length", minimum=0, when=when("shape", "flat_plate", "rectangular_block")),
        qty("width", "Largura do suporte", "length", minimum=0, when=when("shape", "flat_plate", "rectangular_block")),
        qty("thickness", "Espessura do suporte", "length", minimum=0, when=when("shape", "flat_plate", "rectangular_block")),
        text("coordinate_system", "Sistema de coordenadas (origem e sentido dos eixos)", minimum=10, multiline=True),
        vector("position", "Posição da origem do suporte nesse sistema"),
        enum("orientation", "Normal da face em contato com a amostra", AXES),
        enum("contact", "Contato térmico com a amostra", [("full", "Contato total"), ("partial", "Contato parcial"),
                                                          ("gap", "Separado por folga/ar"), ("unknown", "Não informado na fonte")]),
        text("material_name", "Material do suporte (como consta na fonte)", minimum=2, maximum=200,
             help="O nome do material não define propriedades: registre-as abaixo com fonte, se existirem."),
        property_rows("thermal_properties", "Propriedades térmicas do suporte (opcional)", THERMAL_PROPERTIES, required=False),
    ], validation="DATA_CONTRACT_ONLY",
        development=["Representação do suporte como obstrução/camada no gerador do perfil PMMA (não implementado).",
                     "Modelo de material do suporte com propriedades revisadas (troca de calor com a amostra)."]),
    "duct_geometry": _c("duct_geometry", "GEOMETRY", "Dimensões efetivas do duto", [
        enum("shape", "Forma da seção do duto", [("rectangular", "Retangular"), ("circular", "Circular"), ("other", "Outra (descrever)")]),
        text("shape_description", "Descrição da forma", minimum=10, when=when("shape", "other")),
        qty("width", "Largura interna", "length", minimum=0, when=when("shape", "rectangular")),
        qty("height", "Altura interna", "length", minimum=0, when=when("shape", "rectangular")),
        qty("diameter", "Diâmetro interno", "length", minimum=0, when=when("shape", "circular")),
        qty("length", "Comprimento do duto", "length", minimum=0),
        text("coordinate_system", "Sistema de coordenadas (origem e sentido dos eixos)", minimum=10, multiline=True),
        vector("sample_position", "Posição da borda de ataque da amostra"),
        enum("sample_orientation", "Normal da face exposta da amostra", AXES),
        enum("flow_direction", "Sentido do escoamento", AXES),
    ], validation="DATA_CONTRACT_ONLY",
        development=["Mapeamento do duto e da amostra para MESH/OBST/VENT no gerador do perfil PMMA (não implementado).",
                     "Verificação de consistência entre duto, amostra e malha."]),
    "inlet_flow_profile": _c("inlet_flow_profile", "PROCEDURE", "Perfil de escoamento na entrada", [
        enum("profile_type", "Tipo de perfil espacial", [("uniform", "Uniforme"), ("developed", "Desenvolvido (parabólico)"),
                                                         ("measured", "Medido (tabela)"), ("other", "Outro (descrever)")]),
        text("profile_description", "Descrição do perfil", minimum=10, multiline=True, when=when("profile_type", "other", "measured")),
        qty("reference_velocity", "Velocidade de referência", "velocity", minimum=0),
        enum("direction", "Sentido do escoamento", AXES),
        enum("temporal_behavior", "Variação temporal", [("steady", "Constante"), ("ramp", "Rampa"), ("table", "Série temporal")]),
        qty("ramp_duration", "Duração da rampa", "time", minimum=0, when=when("temporal_behavior", "ramp")),
        rows("velocity_series", "Série temporal da velocidade",
             [qty("time", "Tempo", "time", minimum=0, min_exclusive=False), qty("velocity", "Velocidade", "velocity", minimum=0, min_exclusive=False)],
             min_rows=2, increasing="time", when=when("temporal_behavior", "table")),
        qty("inlet_temperature", "Temperatura do ar na entrada", "temperature", minimum=0, required=False),
        enum("regime", "Regime do escoamento", [("laminar", "Laminar"), ("turbulent", "Turbulento"), ("unknown", "Não informado")]),
    ], validation="DATA_CONTRACT_ONLY",
        development=["Condição de contorno de entrada (VENT/SURF com perfil e rampa) no gerador do perfil PMMA (não implementado)."]),
    "anemometer_location": _c("anemometer_location", "MEASUREMENT", "Posição do anemômetro", [
        enum("observed_quantity", "Grandeza observada", [("air_velocity", "Velocidade do ar")]),
        text("instrument", "Instrumento", minimum=3, maximum=300),
        text("coordinate_system", "Sistema de coordenadas (origem e sentido dos eixos)", minimum=10, multiline=True),
        vector("position", "Posição do ponto de medição"),
        text("criterion", "Critério de medição (quando e como a leitura foi feita)", minimum=10, multiline=True),
        qty("uncertainty", "Incerteza da leitura", "velocity", minimum=0, min_exclusive=False, required=False),
    ], hypothesis="DRAFT_ONLY", validation="DATA_CONTRACT_ONLY",
        development=["Uso da posição medida para avaliar a fidelidade do contorno de entrada (não implementado)."]),
    "ignition_procedure": _c("ignition_procedure", "PROCEDURE", "Procedimento de ignição", [
        enum("ignition_type", "Tipo de ignição", [("hot_wire", "Fio aquecido"), ("radiant", "Fonte radiante"),
                                                  ("pilot_flame", "Chama piloto"), ("spark", "Centelha"), ("other", "Outro (descrever)")]),
        text("ignition_description", "Descrição do ignitor", minimum=10, multiline=True, when=when("ignition_type", "other")),
        text("initial_conditions", "Condições iniciais (amostra, escoamento, atmosfera)", minimum=10, multiline=True),
        qty("start_time", "Início da ignição", "time", minimum=0, min_exclusive=False),
        qty("duration", "Duração da ignição", "time", minimum=0),
        enum("temporal_variation", "Variação temporal da fonte", [("constant", "Constante"), ("ramp", "Rampa"),
                                                                    ("pulse", "Pulso"), ("unspecified", "Não informada")]),
        text("coordinate_system", "Sistema de coordenadas (origem e sentido dos eixos)", minimum=10, multiline=True),
        vector("position", "Posição da fonte de ignição"),
        rows("source_quantities", "Grandezas da fonte (opcional)", [
            enum("quantity", "Grandeza", [("power", "Potência", {"dimension": "power"}), ("heat_flux", "Fluxo de calor", {"dimension": "heat_flux"}),
                                          ("temperature", "Temperatura", {"dimension": "temperature"})]),
            qty("value", "Valor", None, minimum=0) | {"dimension_from": "quantity"},
        ], required=False, unique_by="quantity", max_rows=3),
    ], validation="DATA_CONTRACT_ONLY",
        development=["Representação da ignição (superfície aquecida/fonte temporária) no gerador do perfil PMMA (não implementado)."]),
    "pmma_pyrolysis_properties": _c("pmma_pyrolysis_properties", "MATERIAL", "Propriedades termoquímicas e de pirólise", [
        text("material_name", "Material (como definido na fonte)", minimum=2, maximum=200),
        enum("material_model", "Estrutura do modelo de material", [
            ("single_step_arrhenius", "Pirólise em uma etapa (Arrhenius)"), ("inert_thermal", "Somente térmico (sem pirólise)"),
            ("other", "Outro modelo (descrever)")]),
        text("model_description", "Descrição do modelo", minimum=10, multiline=True, when=when("material_model", "other")),
        property_rows("properties", "Propriedades com fonte e validade", PROPERTIES,
                      help="Cada propriedade exige valor, unidade, fonte e condições de validade. Não use valores presumidos pelo nome do material."),
    ], hypothesis="DRAFT_ONLY", validation="DATA_CONTRACT_ONLY",
        intro="O nome do material não determina suas propriedades. Registre somente valores com fonte identificável.",
        development=["Modelo de material (MATL/REAC) revisado por especialista no perfil PMMA (não implementado).",
                     "Verificação/calibração da cinética e das propriedades; revisão do modelo de material (material_model_review)."]),
    "o2_time_profile": _c("o2_time_profile", "PROCEDURE", "Perfil temporal do oxigênio", [
        enum("profile_type", "Forma do perfil", [("constant", "Constante"), ("table", "Série temporal")]),
        qty("constant_fraction", "Fração de O₂", "fraction", minimum=0, maximum=1, min_exclusive=False, when=when("profile_type", "constant")),
        rows("series", "Série temporal da fração de O₂",
             [qty("time", "Tempo", "time", minimum=0, min_exclusive=False), qty("fraction", "Fração de O₂", "fraction", minimum=0, maximum=1, min_exclusive=False)],
             min_rows=2, increasing="time", when=when("profile_type", "table")),
        enum("basis", "Base da fração", [("volume", "Volumétrica/molar"), ("mass", "Mássica"), ("unknown", "Não informada")]),
    ], hypothesis="DRAFT_ONLY", validation="DATA_CONTRACT_ONLY",
        development=["Condição de contorno de composição variável no tempo; o perfil atual não consome esta informação."]),
    "measurement_uncertainty": _c("measurement_uncertainty", "MEASUREMENT", "Incertezas de medição", [
        rows("uncertainties", "Incertezas por grandeza", [
            enum("quantity", "Grandeza medida", [
                ("flame_spread_rate", "Velocidade de propagação", {"dimension": "velocity"}),
                ("airflow_velocity", "Velocidade do ar", {"dimension": "velocity"}),
                ("o2_fraction", "Fração de O₂", {"dimension": "fraction"}),
                ("burn_duration", "Duração da queima", {"dimension": "time"})]),
            enum("type", "Tipo", [("standard", "Padrão (1σ)"), ("expanded", "Expandida"), ("bound", "Limite (±)")]),
            qty("value", "Valor", None, minimum=0, min_exclusive=False) | {"dimension_from": "quantity"},
            text("method", "Como foi estimada", minimum=5, maximum=600),
        ], unique_by="quantity", max_rows=4),
    ], hypothesis="DRAFT_ONLY", validation="DATA_CONTRACT_ONLY",
        development=["Comparação quantitativa entre resultado calculado e medição (não implementada). Não é entrada FDS."]),
    "flame_front_tracking_method": _c("flame_front_tracking_method", "MEASUREMENT", "Método de rastreamento da frente de chama", [
        enum("method", "Método", [("video_edge", "Detecção de borda em vídeo"), ("intensity_threshold", "Limiar de intensidade"),
                                  ("thermocouple_arrival", "Chegada em termopares"), ("other", "Outro (descrever)")]),
        text("method_description", "Descrição do método", minimum=10, multiline=True, when=when("method", "other")),
        enum("observed_quantity", "Grandeza observada", [("front_position", "Posição da frente"), ("spread_rate", "Velocidade de propagação")]),
        text("criterion", "Critério que define a frente", minimum=10, multiline=True),
        qty("analysis_start", "Início do intervalo de análise", "time", minimum=0, min_exclusive=False),
        qty("analysis_end", "Fim do intervalo de análise", "time", minimum=0),
        enum("calculation", "Cálculo da velocidade", [("linear_fit", "Ajuste linear posição × tempo"),
                                                       ("finite_difference", "Diferenças finitas"), ("other", "Outro")]),
        qty("uncertainty", "Incerteza da velocidade", "velocity", minimum=0, min_exclusive=False, required=False),
    ], hypothesis="DRAFT_ONLY", validation="DATA_CONTRACT_ONLY",
        development=["Pós-processamento que extraia a frente de chama do cálculo com o mesmo critério (não implementado). Não é entrada FDS."]),
}

GENERIC = _c("generic", "DOCUMENT", "Registro documental", [
    text("description", "Descrição estruturada da informação encontrada", minimum=10, maximum=6000, multiline=True)],
    hypothesis="NOT_AVAILABLE", validation="NO_SCHEMA",
    development=["Não existe contrato de dados para este parâmetro. É necessário definir campos, dimensões e unidades "
                 "(contrato) e, depois, como o perfil físico o utilizaria."])


def contract_for(parameter: str) -> dict[str, Any]:
    if parameter in CONTRACTS:
        return CONTRACTS[parameter]
    return {**GENERIC, "parameter": parameter}


def _unit_options(dimension):
    return [{"value": units.display_unit(c), "label_pt": units.display_unit(c)} for c in units.units_of(dimension)]


def export(contract: dict[str, Any]) -> dict[str, Any]:
    """Descrição serializável para o formulário dinâmico (unidades aceitas e SI de cada dimensão)."""
    out = copy.deepcopy(contract)

    def decorate(fields):
        for f in fields:
            if f["type"] in ("quantity", "vector") and f.get("dimension"):
                f["units"] = _unit_options(f["dimension"])
                f["si_unit"] = units.display_unit(units.si_unit_of(f["dimension"]))
                f["dimension_pt"] = units.DIMENSION_PT.get(f["dimension"])
            if f["type"] == "enum":
                for o in f["options"]:
                    if o.get("dimension"):
                        o["units"] = _unit_options(o["dimension"])
                        o["si_unit"] = units.display_unit(units.si_unit_of(o["dimension"]))
            if f["type"] == "rows":
                decorate(f["columns"])
    decorate(out["fields"])
    return out


# ------------------------------------------------------------------ conteúdo de teste
_TEST_PATTERNS = [r"ambiente de test", r"dados? de teste", r"valor(es)? (de|para) teste", r"(apenas|somente|so) (para )?teste",
                  r"para fins de teste", r"teste interno", r"sintetic", r"fictici", r"lorem ipsum", r"placeholder",
                  r"\bdummy\b", r"\bfake\b", r"asdf", r"qwert", r"\bteste\s+teste\b", r"\btest(e|ing)? data\b"]
_TEST_WHOLE = re.compile(r"^\s*(teste?s?|testing|x+|\.+|-+|a+|abc|123+|ok)\s*$")
_TEST_RE = re.compile("|".join(_TEST_PATTERNS))


def _fold(value: str) -> str:
    s = unicodedata.normalize("NFKD", value.casefold())
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def looks_like_test(value: Any) -> bool:
    """Heurística conservadora: frases típicas de preenchimento de teste. Não detecta 'teste' isolado
    dentro de uma frase (ensaios NASA são 'tests')."""
    if not isinstance(value, str) or not value.strip():
        return False
    s = _fold(value)
    return bool(_TEST_RE.search(s) or _TEST_WHOLE.match(s))


def test_like_texts(payload: Any) -> list[str]:
    found = []
    def walk(v):
        if isinstance(v, str):
            if looks_like_test(v):
                found.append(v[:80])
        elif isinstance(v, dict):
            for x in v.values(): walk(x)
        elif isinstance(v, list):
            for x in v: walk(x)
    walk(payload)
    return found


# ------------------------------------------------------------------ validação
def _num(v) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v) if math.isfinite(v) else None


def fmt(value: float) -> str:
    return f"{value:.6g}".replace(".", ",")


class _Out:
    def __init__(self):
        self.errors: list[dict] = []
        self.warnings: list[dict] = []
        self.conversions: list[dict] = []

    def err(self, path, code, message):
        self.errors.append({"field": path, "code": code, "message_pt": message})

    def warn(self, path, code, message):
        self.warnings.append({"field": path, "code": code, "message_pt": message})


def _visible(field, scope):
    cond = field.get("when")
    return not cond or scope.get(cond["field"]) in cond["in"]


def _empty(v):
    """Vazio = sem conteúdo informado. Uma unidade pré-selecionada sem valor não conta como preenchimento."""
    if isinstance(v, dict):
        return all(_empty(x) for k, x in v.items() if k != "unit")
    return v is None or (isinstance(v, str) and not v.strip()) or v == []


def _quantity(field, raw, path, out, dimension):
    label = field["label_pt"]
    if not isinstance(raw, dict):
        out.err(path, "TYPE", f"{label}: informe valor numérico e unidade.")
        return None
    value, unit = _num(raw.get("value")), raw.get("unit")
    if value is None:
        out.err(path, "NUMBER", f"{label}: o valor deve ser um número finito.")
        return None
    if not isinstance(unit, str) or not unit.strip():
        out.err(path, "UNIT_MISSING", f"{label}: informe a unidade.")
        return None
    if dimension is None:
        out.err(path, "DIMENSION_UNDEFINED", f"{label}: escolha primeiro a grandeza/propriedade.")
        return None
    q = units.normalize(value, unit)
    if q is None:
        out.err(path, "UNIT_UNSUPPORTED", f"{label}: unidade “{unit}” não reconhecida.")
        return None
    if q.dimension != dimension:
        out.err(path, "UNIT_DIMENSION", f"{label}: “{unit}” é {units.DIMENSION_PT.get(q.dimension, q.dimension)}, "
                                        f"mas o campo exige {units.DIMENSION_PT.get(dimension, dimension)}.")
        return None
    lo, hi = field.get("min"), field.get("max")
    if lo is not None and (q.value < lo or (field.get("min_exclusive", True) and q.value == lo)):
        rule = "maior que" if field.get("min_exclusive", True) else "maior ou igual a"
        extra = " (temperatura absoluta acima de 0 K)" if dimension == "temperature" else ""
        out.err(path, "DOMAIN", f"{label}: deve ser {rule} {fmt(lo)} {units.display_unit(q.unit)}{extra}.")
        return None
    if hi is not None and q.value > hi:
        out.err(path, "DOMAIN", f"{label}: deve ser no máximo {fmt(hi)} {units.display_unit(q.unit)}.")
        return None
    si = units.display_unit(q.unit)
    if units.canonical_unit(unit) != units.canonical_unit(q.unit) or dimension == "temperature":
        out.conversions.append({"field": path, "label_pt": label, "original": f"{fmt(value)} {unit.strip()}", "si": f"{fmt(q.value)} {si}"})
    return {"value": value, "unit": unit.strip(), "si_value": q.value, "si_unit": q.unit, "dimension": q.dimension}


def _field(field, raw, path, out, scope):
    t = field["type"]
    if t == "quantity":
        dim = field.get("dimension")
        if field.get("dimension_from"):
            opt = next((o for o in scope.get("__options__", {}).get(field["dimension_from"], []) if o["value"] == scope.get(field["dimension_from"])), None)
            dim = opt.get("dimension") if opt else None
        return _quantity(field, raw, path, out, dim)
    if t == "enum":
        if raw not in [o["value"] for o in field["options"]]:
            out.err(path, "OPTION", f"{field['label_pt']}: escolha uma das opções.")
            return None
        return raw
    if t == "text":
        if not isinstance(raw, str):
            out.err(path, "TYPE", f"{field['label_pt']}: texto esperado.")
            return None
        s = raw.strip()
        if len(s) < field.get("min", 0):
            out.err(path, "TEXT_SHORT", f"{field['label_pt']}: mínimo de {field['min']} caracteres.")
            return None
        if len(s) > field.get("max", 2000):
            out.err(path, "TEXT_LONG", f"{field['label_pt']}: máximo de {field['max']} caracteres.")
            return None
        return s
    if t == "vector":
        if not isinstance(raw, dict):
            out.err(path, "TYPE", f"{field['label_pt']}: informe x, y, z e unidade.")
            return None
        result = {}
        for axis in field["axes"]:
            q = _quantity({"label_pt": f"{field['label_pt']} ({axis})", "min": None}, {"value": raw.get(axis), "unit": raw.get("unit")},
                          f"{path}.{axis}", out, field["dimension"])
            if q is None:
                return None
            result[axis] = q["si_value"]
        return {"x": raw.get("x"), "y": raw.get("y"), "z": raw.get("z"), "unit": str(raw.get("unit")).strip(),
                "si": result, "si_unit": units.si_unit_of(field["dimension"])}
    if t == "rows":
        if not isinstance(raw, list):
            out.err(path, "TYPE", f"{field['label_pt']}: lista esperada.")
            return None
        if len(raw) < field["min_rows"]:
            out.err(path, "ROWS_MIN", f"{field['label_pt']}: informe ao menos {field['min_rows']} linha(s).")
        if len(raw) > field["max_rows"]:
            out.err(path, "ROWS_MAX", f"{field['label_pt']}: no máximo {field['max_rows']} linha(s).")
            return None
        options = {c["name"]: c["options"] for c in field["columns"] if c["type"] == "enum"}
        result = []
        for i, row in enumerate(raw):
            if not isinstance(row, dict):
                out.err(f"{path}[{i}]", "TYPE", f"{field['label_pt']}, linha {i + 1}: formato inválido.")
                continue
            result.append(_object(field["columns"], {**row, "__options__": options}, f"{path}[{i}]", out, f"linha {i + 1}"))
        key = field.get("unique_by")
        if key:
            seen = [r.get(key) for r in result if r and r.get(key)]
            if len(seen) != len(set(seen)):
                out.err(path, "DUPLICATE", f"{field['label_pt']}: cada {key.replace('_', ' ')} pode aparecer uma única vez.")
        inc = field.get("increasing")
        if inc:
            series = [r[inc]["si_value"] for r in result if r and isinstance(r.get(inc), dict)]
            if any(b <= a for a, b in zip(series, series[1:])):
                out.err(path, "NOT_INCREASING", f"{field['label_pt']}: os tempos devem ser estritamente crescentes.")
        return result
    raise ValueError(f"tipo de campo desconhecido: {t}")


def _object(fields, payload, path, out, where=""):
    result = {}
    for f in fields:
        if not _visible(f, payload):
            continue
        p = f"{path}.{f['name']}" if path else f["name"]
        raw = payload.get(f["name"])
        if _empty(raw):
            if f.get("required", True):
                prefix = f"{where}: " if where else ""
                out.err(p, "REQUIRED", f"{prefix}{f['label_pt']} é obrigatório.")
            continue
        value = _field(f, raw, p, out, payload)
        if value is not None:
            result[f["name"]] = value
    return result


def validate(contract: dict[str, Any], payload: Any) -> dict[str, Any]:
    out = _Out()
    if not isinstance(payload, dict):
        out.err("", "TYPE", "Informe os campos estruturados do formulário.")
        return {"errors": out.errors, "warnings": [], "conversions": [], "values": {}, "completeness": None}
    known = {f["name"] for f in contract["fields"]}
    for extra in sorted(set(payload) - known):
        out.err(extra, "UNKNOWN_FIELD", f"Campo não previsto no contrato: {extra}.")
    values = _object(contract["fields"], payload, "", out)
    completeness = _completeness(contract, values)
    _cross(contract, values, out)
    return {"errors": out.errors, "warnings": out.warnings, "conversions": out.conversions, "values": values, "completeness": completeness}


def _completeness(contract, values):
    if contract["kind"] != "MATERIAL":
        return None
    required = MODEL_REQUIRED.get(values.get("material_model"), [])
    present = [r["property"] for r in values.get("properties", []) if r and r.get("property") and r.get("value")]
    missing = [p for p in required if p not in present]
    return {"model": values.get("material_model"), "required": required, "present": present, "missing": missing,
            "missing_pt": [PROPERTY_LABEL[p] for p in missing],
            "note_pt": None if required else "Modelo descrito livremente: o conjunto de propriedades exigido não está definido no contrato."}


def _cross(contract, values, out):
    p = contract["parameter"]
    if p == "flame_front_tracking_method":
        a, b = values.get("analysis_start"), values.get("analysis_end")
        if a and b and b["si_value"] <= a["si_value"]:
            out.err("analysis_end", "INTERVAL", "O fim do intervalo de análise deve ser posterior ao início.")


def context_checks(parameter: str, values: dict[str, Any], published: dict[str, units.Quantity]) -> tuple[list[dict], list[dict]]:
    """Coerência determinística com os valores PUBLICADOS e conferidos (nunca os altera)."""
    errors, warnings = [], []
    thickness, width = published.get("thickness"), published.get("width")
    if parameter == "sample_length" and thickness and values.get("quantity"):
        if values["quantity"]["si_value"] <= thickness.value:
            errors.append({"field": "quantity", "code": "CONSISTENCY",
                           "message_pt": "O comprimento deve exceder a espessura documentada da amostra; confirme a dimensão e a fonte."})
    if parameter == "duct_geometry" and width:
        for key in ("width", "diameter"):
            if values.get(key) and values[key]["si_value"] < width.value:
                errors.append({"field": key, "code": "CONSISTENCY",
                               "message_pt": f"A seção do duto ({fmt(values[key]['si_value'])} m) é menor que a largura publicada da amostra ({fmt(width.value)} m)."})
    if parameter == "sample_holder_substrate" and width and values.get("width") and values["width"]["si_value"] < width.value:
        warnings.append({"field": "width", "code": "CONSISTENCY",
                         "message_pt": f"O suporte é mais estreito que a largura publicada da amostra ({fmt(width.value)} m); confirme na fonte."})
    flow = published.get("airflow_velocity")
    if parameter == "inlet_flow_profile" and flow and values.get("reference_velocity"):
        v = values["reference_velocity"]["si_value"]
        if not math.isclose(v, flow.value, rel_tol=1e-6):
            warnings.append({"field": "reference_velocity", "code": "DIFFERS_FROM_PUBLISHED",
                             "message_pt": f"Difere da velocidade publicada ({fmt(flow.value)} m/s). O valor publicado não será alterado; justifique a diferença."})
    o2 = published.get("o2_initial")
    if parameter == "o2_time_profile" and o2:
        first = values.get("constant_fraction") or ((values.get("series") or [{}])[0] or {}).get("fraction")
        if first and not math.isclose(first["si_value"], o2.value, rel_tol=1e-6):
            warnings.append({"field": "series", "code": "DIFFERS_FROM_PUBLISHED",
                             "message_pt": f"O valor inicial difere do O₂ inicial publicado ({fmt(o2.value)}). O valor publicado não será alterado."})
    return errors, warnings


def summary_pt(contract: dict[str, Any], values: dict[str, Any]) -> str:
    """Resumo humano do que foi registrado (para histórico, preparação e consequências)."""
    parts = []
    def show(f, v):
        if v is None:
            return None
        if f["type"] == "quantity":
            return f"{fmt(v['value'])} {v['unit']}"
        if f["type"] == "enum":
            return next((o["label_pt"] for o in f["options"] if o["value"] == v), v)
        if f["type"] == "vector":
            return f"({fmt(v['x'])}; {fmt(v['y'])}; {fmt(v['z'])}) {v['unit']}"
        if f["type"] == "rows":
            return f"{len(v)} linha(s)"
        return v if len(v) <= 60 else v[:57] + "…"
    for f in contract["fields"]:
        if f["name"] in values:
            text_ = show(f, values[f["name"]])
            if text_ is not None:
                parts.append(text_ if contract["kind"] == "QUANTITY" else f"{f['label_pt']}: {text_}")
    return "; ".join(parts)


def diff(before: Any, after: Any, path: str = "") -> list[dict]:
    """Diferenças campo a campo entre duas propostas (edição auditável)."""
    if isinstance(before, dict) and isinstance(after, dict):
        changes = []
        for k in sorted(set(before) | set(after)):
            changes += diff(before.get(k), after.get(k), f"{path}.{k}" if path else k)
        return changes
    if before != after:
        return [{"field": path, "before": before, "after": after}]
    return []
