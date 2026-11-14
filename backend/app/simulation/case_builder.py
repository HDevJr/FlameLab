"""FDS Case Builder — gerador determinístico de arquivos `.fds`.

- Recebe somente valores numéricos validados contra a faixa do modelo; nunca texto livre,
  nunca código FDS vindo do usuário ou da IA.
- O mesmo conjunto de valores gera sempre o mesmo arquivo (mesmo SHA-256).
- Só modelos com `implemented=True` têm template.
"""

from __future__ import annotations

import hashlib
import math

from backend.app.simulation.models import SimulationModel
from backend.app.simulation.registry import INTEGRATION


class CaseValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


_TEMPLATES = {
    INTEGRATION.model_id: """\
&HEAD CHID='{chid}', TITLE='FlameLab integration test - not a NASA experiment reproduction' /

&MESH IJK=36,24,24, XB=0.0,3.6,0.0,2.4,0.0,2.4 /

&TIME T_END={t_end} /
&DUMP NFRAMES={nframes} /

&REAC FUEL='PROPANE', SOOT_YIELD={soot_yield} /

&SURF ID='BURNER', HRRPUA={hrrpua}, COLOR='RED' /

&OBST XB=0.0,0.4,1.0,1.4,0.0,0.2 /
&VENT XB=0.0,0.4,1.0,1.4,0.2,0.2, SURF_ID='BURNER' /

&VENT XB=3.6,3.6,0.8,1.6,0.0,2.0, SURF_ID='OPEN' /

&DEVC ID='T_ceiling', QUANTITY='TEMPERATURE', XYZ=1.8,1.2,2.3 /
&DEVC ID='T_door_top', QUANTITY='TEMPERATURE', XYZ=3.5,1.2,1.9 /

&BNDF QUANTITY='GAUGE HEAT FLUX' /

&SLCF PBY=1.2, QUANTITY='TEMPERATURE', VECTOR=.TRUE. /

&TAIL /
""",
}


def _fmt(value: float) -> str:
    text = f"{value:.6g}"
    return text if any(c in text for c in ".e") else text + "."


def validate_values(model: SimulationModel, values: dict[str, float]) -> dict[str, float]:
    known = {p.name: p for p in model.parameters}
    errors = [f"parâmetro não editável: {name}" for name in values if name not in known]
    out: dict[str, float] = {}
    for name, spec in known.items():
        raw = values.get(name, spec.default)
        if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(raw):
            errors.append(f"{name}: valor numérico inválido")
            continue
        if not spec.min <= raw <= spec.max:
            errors.append(f"{name}: {raw} fora da faixa permitida [{spec.min}, {spec.max}] {spec.unit}")
            continue
        out[name] = float(raw)
    if errors:
        raise CaseValidationError(errors)
    return out


def build_case(model: SimulationModel, values: dict[str, float], chid: str) -> tuple[str, str]:
    """Devolve (texto .fds, sha256). `chid` é gerado pelo servidor (alfanumérico)."""
    if not model.implemented or model.model_id not in _TEMPLATES:
        raise CaseValidationError([f"modelo {model.model_id} não tem gerador aprovado"])
    if not chid.replace("_", "").isalnum() or len(chid) > 40:
        raise CaseValidationError(["CHID inválido"])
    v = validate_values(model, values)
    text = _TEMPLATES[model.model_id].format(
        chid=chid, t_end=_fmt(v["t_end"]), soot_yield=_fmt(v["soot_yield"]), hrrpua=_fmt(v["hrrpua"]),
        nframes=int(max(10, min(200, v["t_end"] * 5))),
    )
    return text, hashlib.sha256(text.encode("utf-8")).hexdigest()
