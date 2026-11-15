"""Contratos de simulação (ADR-09): SimulationModel, Scenario, SimulationRun, RenderedArtifact."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class RunState(str, Enum):
    QUEUED = "QUEUED"
    VALIDATING = "VALIDATING"
    RUNNING_FDS = "RUNNING_FDS"
    PROCESSING_RESULTS = "PROCESSING_RESULTS"
    RENDERING = "RENDERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


TERMINAL = frozenset({RunState.COMPLETED, RunState.FAILED, RunState.BLOCKED})


class Compatibility(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    MISSING_PARAMETERS = "MISSING_PARAMETERS"
    UNSUPPORTED_PHYSICS = "UNSUPPORTED_PHYSICS"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


class EditableParameter(BaseModel):
    """Parâmetro que o gerador aceita. Faixas e unidades são do modelo, não do usuário."""

    name: str
    label_pt: str
    group: Literal["EXPERIMENTAL", "NUMERICO", "HIPOTESE", "MATERIAL", "GEOMETRIA", "CONTORNO", "SAIDA"]
    unit: str
    default: float
    min: float
    max: float
    step: float | None = None
    help_pt: str | None = None


class SimulationModel(BaseModel):
    model_id: str
    engine: Literal["FDS"] = "FDS"
    title_pt: str
    purpose: Literal["INTEGRATION_TEST", "REPRODUCTION"]
    label_pt: str  # rótulo que acompanha todo resultado deste modelo
    description_pt: str
    phenomena: list[str]
    implemented: bool  # existe gerador aprovado?
    template_source: dict[str, Any] | None = None  # origem do caso-base (ex.: exemplo oficial do FDS)
    parameters: list[EditableParameter] = Field(default_factory=list)
    required_inputs: list[str] = Field(default_factory=list)  # parâmetros de experimento exigidos


class ParameterChange(BaseModel):
    name: str
    from_value: float
    to_value: float
    unit: str
    label_pt: str | None = None
    base_status: str | None = None  # estado de revisão do valor original no momento da alteração


class Scenario(BaseModel):
    case_id: str | None = None
    case_version: int | None = None
    scenario_id: str
    kind: Literal["BASE", "DERIVED"]
    model_id: str | None = None  # cenário executável (modelo de simulação)
    experiment_id: str | None = None  # cenário de hipótese sobre um experimento
    scope: Literal["EXPERIMENT", "DEMO"] = "DEMO"
    hypothesis_pt: str | None = None
    title_pt: str
    changes: list[ParameterChange] = Field(default_factory=list)
    values: dict[str, float] = Field(default_factory=dict)
    status: Literal["HIPOTESE_COMPUTACIONAL"] = "HIPOTESE_COMPUTACIONAL"
    executable: bool
    blocked_reasons_pt: list[str] = Field(default_factory=list)
    created_at: str
    note_pt: str


class RenderedArtifact(BaseModel):
    kind: Literal["VIDEO_MP4", "FRAME_PNG", "CSV", "LOG", "FDS_INPUT", "SMV_SCRIPT", "MANIFEST_JSON"]
    name: str
    sha256: str
    size_bytes: int
    meta: dict[str, Any] = Field(default_factory=dict)


class SimulationRun(BaseModel):
    case_id: str | None = None
    case_version: int | None = None
    run_id: str
    scenario_id: str
    model_id: str
    purpose: str
    label_pt: str
    state: RunState
    demo: bool = False  # True somente em execuções do executor simulado (testes)
    scope: Literal["EXPERIMENT", "DEMO"] = "DEMO"
    fds_sha256: str | None = None
    fds_version: str | None = None
    smokeview_version: str | None = None
    ffmpeg_version: str | None = None
    parameters: dict[str, float] = Field(default_factory=dict)
    changes: list[ParameterChange] = Field(default_factory=list)
    timestamps: dict[str, str] = Field(default_factory=dict)
    log_tail: list[str] = Field(default_factory=list)
    failure_reason: str | None = None
    artifacts: list[RenderedArtifact] = Field(default_factory=list)
    results: dict[str, Any] = Field(default_factory=dict)
    limits: dict[str, Any] = Field(default_factory=dict)
    timings_ms: dict[str, int | None] = Field(default_factory=dict)
