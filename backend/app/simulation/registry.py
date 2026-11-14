"""Modelos de simulação conhecidos pelo FlameLab.

Um modelo só é executável quando tem gerador aprovado (`implemented=True`). Nesta versão:
- `fds-integration-simple-fire`: caso de TESTE DE INTEGRAÇÃO derivado do exemplo oficial
  `Examples/Fires/simple_test.fds` do FDS 6.11.1. Não representa nenhum experimento NASA.
- `fds-flame-spread-thin-solid`: modelo de reprodução de propagação de chama em sólido fino
  sob escoamento. NÃO implementado: a lista de entradas exigidas serve para avaliar a
  compatibilidade de experimentos e explicar o bloqueio.
"""

from __future__ import annotations

from backend.app.simulation.models import EditableParameter, SimulationModel

INTEGRATION = SimulationModel(
    model_id="fds-integration-simple-fire",
    title_pt="Caso de integração FDS — queimador em compartimento",
    purpose="INTEGRATION_TEST",
    label_pt="Teste de integração do pipeline FDS/Smokeview — não é reprodução de experimento NASA",
    description_pt=(
        "Queimador de propano em uma sala de 3,6 × 2,4 × 2,4 m com uma abertura. Serve para provar que o "
        "FlameLab gera, executa, renderiza e publica um caso FDS. Os resultados não têm relação com dados NASA."
    ),
    phenomena=["fire"],
    implemented=True,
    template_source={
        "origin": "FDS 6.11.1 — Examples/Fires/simple_test.fds (exemplo oficial distribuído com o FDS)",
        "sha256": "registrado em docs/evidence/fds_smokeview_spike_*.json",
        "changes_pt": "CHID, T_END, HRRPUA e SOOT_YIELD parametrizados; saídas DEVC/SLCF fixas.",
    },
    parameters=[
        EditableParameter(name="hrrpua", label_pt="Potência por área do queimador", group="CONTORNO",
                          unit="kW/m²", default=1000.0, min=250.0, max=2000.0, step=50.0,
                          help_pt="HRRPUA da superfície do queimador (0,16 m²)."),
        EditableParameter(name="soot_yield", label_pt="Rendimento de fuligem", group="HIPOTESE",
                          unit="kg/kg", default=0.01, min=0.0, max=0.1, step=0.005,
                          help_pt="Fração da massa de combustível convertida em fuligem."),
        EditableParameter(name="t_end", label_pt="Tempo simulado", group="NUMERICO", unit="s",
                          default=10.0, min=5.0, max=60.0, step=5.0,
                          help_pt="Duração da simulação. Referência nesta máquina (4 threads): 5 s simulados levaram ~1 min de cálculo; 60 s, ~5 min."),
    ],
)

FLAME_SPREAD = SimulationModel(
    model_id="fds-flame-spread-thin-solid",
    title_pt="Propagação de chama em sólido sob escoamento (reprodução)",
    purpose="REPRODUCTION",
    label_pt="Tentativa de reprodução numérica — exige parâmetros conferidos e modelo aprovado",
    description_pt=(
        "Modelo planejado para ensaios de propagação de chama em amostras sólidas em duto com escoamento. "
        "O gerador ainda não existe: nenhum caso é produzido."
    ),
    phenomena=["flame_spread", "combustion", "pyrolysis"],
    implemented=False,
    required_inputs=[
        "material", "thickness", "width", "sample_length", "airflow_velocity", "o2_initial",
        "ambient_pressure", "ambient_temperature", "duct_geometry", "inlet_flow_profile",
        "sample_holder_substrate", "ignition_procedure", "material_pyrolysis_properties",
    ],
)

MODELS: dict[str, SimulationModel] = {m.model_id: m for m in (INTEGRATION, FLAME_SPREAD)}

# Fenômenos que algum motor integrado sabe tratar. Fora disso: UNSUPPORTED_PHYSICS.
FDS_PHENOMENA = frozenset({"fire", "combustion", "flame_spread", "pyrolysis", "smoke_transport"})
