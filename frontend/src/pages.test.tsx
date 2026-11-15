// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, type Compatibility, type Experiment, type Run, type Scenario, type SimModel, type SimStatus } from "./api";
import DemoFds from "./pages/DemoFds";
import Result from "./pages/Result";
import RunPage from "./pages/RunPage";
import ScenarioPage from "./pages/Scenario";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });
beforeEach(() => {
  Object.defineProperty(HTMLMediaElement.prototype, "play", { configurable: true, value: vi.fn(() => Promise.resolve()) });
});

const at = (path: string, route: string, el: JSX.Element) =>
  render(<MemoryRouter initialEntries={[path]}><Routes><Route path={route} element={el} /></Routes></MemoryRouter>);

const status: SimStatus = { executor: "local-windows-fds", available: true, detail: "ok", demo: false, versions: { fds: "FDS-6.11.1", smokeview: "SMV-6.11.2", ffmpeg: "9.0.2" }, limits: {} };
const baseRun = (o: Partial<Run>): Run => ({
  run_id: "RUN-1", scenario_id: "SCN-1", model_id: "m", purpose: "INTEGRATION_TEST", label_pt: "Teste de integração — não é reprodução de experimento NASA",
  state: "RUNNING_FDS", demo: false, scope: "DEMO", fds_sha256: "a".repeat(64), fds_version: "FDS-6.11.1", smokeview_version: "SMV", ffmpeg_version: "9",
  parameters: { t_end: 10 }, changes: [], timestamps: { QUEUED: new Date(Date.now() - 65000).toISOString() }, failure_reason: null, artifacts: [], timings_ms: {},
  progress: null, results: {}, log_tail: [], ...o,
});
const scenario = (o: Partial<Scenario>): Scenario => ({
  scenario_id: "SCN-1", kind: "BASE", model_id: "m", experiment_id: null, scope: "DEMO", title_pt: "Caso", hypothesis_pt: null, changes: [], values: { t_end: 10 },
  executable: true, blocked_reasons_pt: [], note_pt: "nota", status: "HIPOTESE_COMPUTACIONAL", ...o,
});

describe("S06 — estados longos de execução", () => {
  const mount = (run: Run, sc = scenario({})) => {
    vi.spyOn(api, "scenario").mockResolvedValue(sc);
    vi.spyOn(api, "simStatus").mockResolvedValue(status);
    vi.spyOn(api, "runs").mockResolvedValue([run]);
    vi.spyOn(api, "run").mockResolvedValue(run);
    return at("/simulacao/SCN-1", "/simulacao/:scenarioId", <RunPage />);
  };
  it("diz que o FDS está executando e mostra tempo decorrido real; progresso físico do log quando existe", async () => {
    mount(baseRun({ progress: { simulated_time_s: 2.5, t_end_s: 10, fraction: 0.25, source: "log do FDS" } }));
    await waitFor(() => expect(screen.getByText("O FDS está executando o cálculo.")).toBeTruthy());
    expect(screen.getByText(/1 min 0\d s|1 min 1\d s/)).toBeTruthy(); // ≈ 65 s desde QUEUED
    expect(screen.getByRole("progressbar").getAttribute("aria-valuenow")).toBe("25");
    expect(screen.getByText(/2,50 s de 10 s/)).toBeTruthy();
    expect(screen.getByText(/não é previsão de quando termina/)).toBeTruthy();
  });
  it("sem informação confiável de progresso, mostra estado indeterminado e só o tempo decorrido", async () => {
    mount(baseRun({ progress: null }));
    await waitFor(() => expect(screen.getByLabelText("Progresso indeterminado")).toBeTruthy());
    expect(screen.queryByRole("progressbar")).toBeNull();
    expect(screen.getByText(/Sem informação confiável de progresso/)).toBeTruthy();
  });
  it("ao concluir mostra os tempos medidos e o acesso ao resultado", async () => {
    mount(baseRun({ state: "COMPLETED", timings_ms: { queue_wait: 0, preparation: 250, fds: 74719, smokeview: 4578, mp4_encoding: 452, total: 80062 } }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Ver resultado e vídeo" })).toBeTruthy());
    expect(screen.getByText("1 min 15 s")).toBeTruthy(); // FDS 74,7 s
    expect(screen.getByText("Renderização no Smokeview")).toBeTruthy();
  });
  it("cenário de hipótese sobre experimento é bloqueado e não é apresentado como demonstração", async () => {
    vi.spyOn(api, "scenario").mockResolvedValue(scenario({ scope: "EXPERIMENT", experiment_id: "EXP-1", model_id: null, kind: "DERIVED", executable: false,
      blocked_reasons_pt: ["Faltam 5 informações necessárias ao modelo."], changes: [{ name: "airflow_velocity", from_value: 9, to_value: 12, unit: "cm/s", label_pt: "Velocidade do ar", base_status: "EXTRAIDO_NAO_REVISADO" }] }));
    vi.spyOn(api, "simStatus").mockResolvedValue(status);
    vi.spyOn(api, "runs").mockResolvedValue([]);
    at("/simulacao/SCN-1", "/simulacao/:scenarioId", <RunPage />);
    await waitFor(() => expect(screen.getByText(/Este cenário não pode ser executado/)).toBeTruthy());
    expect(screen.getByText(/Nenhuma simulação genérica é usada no lugar/)).toBeTruthy();
    expect(screen.getByText("valor original não revisado")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Iniciar simulação" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.queryByText(/Demonstração FDS:/)).toBeNull();
  });
});

describe("separação artigo × demonstração FDS", () => {
  const model: SimModel = { model_id: "m", title_pt: "Caso de integração FDS — queimador em compartimento", purpose: "INTEGRATION_TEST", label_pt: "x", description_pt: "Queimador de propano em uma sala.",
    implemented: true, required_inputs: [], template_source: { origin: "FDS 6.11.1 — exemplo oficial" },
    parameters: [{ name: "hrrpua", label_pt: "Potência por área do queimador", group: "CONTORNO", unit: "kW/m²", default: 1000, min: 250, max: 2000, step: 50, help_pt: null }] };

  it("a Demonstração FDS declara que NÃO é um experimento NASA", async () => {
    vi.spyOn(api, "models").mockResolvedValue([model]);
    at("/demonstracao-fds", "/demonstracao-fds", <DemoFds />);
    await waitFor(() => expect(screen.getByText("Isto não é um experimento NASA.")).toBeTruthy());
    expect(screen.getByText("Potência por área do queimador")).toBeTruthy();
  });

  it("alterar parâmetros do experimento mostra só condições dele — nunca o queimador, nem resultados observados", async () => {
    const exp = { experiment_id: "EXP-1", label: "M1", document_id: "D", document_title: "Doc", description: null, phenomena: [], origin: "CURATED", gaps: [], review: { total: 2, reviewed: 0, pending: 2, gaps: 0 },
      parameters: [
        { record_id: "r1", parameter: "airflow_velocity", label_pt: "Velocidade do ar", role: "CONDICAO", nature: "OBSERVADO", status: "EXTRAIDO_NAO_REVISADO", original: { value: 9, unit: "cm/s" }, normalized: null, evidence: [], caveats_pt: [] },
        { record_id: "r2", parameter: "flame_spread_rate", label_pt: "Velocidade de propagação", role: "OBSERVAVEL", nature: "OBSERVADO", status: "EXTRAIDO_NAO_REVISADO", original: { value: 0.071, unit: "mm/s" }, normalized: null, evidence: [], caveats_pt: [] },
      ] } as Experiment;
    const compat: Compatibility = { experiment_id: "EXP-1", status: "MISSING_PARAMETERS", reasons_pt: ["Faltam 5 informações necessárias ao modelo (lacunas registradas)."], missing: ["duct_geometry"], unreviewed: [],
      editable_conditions: ["airflow_velocity"], editable: [{ parameter: "airflow_velocity", label_pt: "Velocidade do ar", value: 9, unit: "cm/s", status: "EXTRAIDO_NAO_REVISADO", rule_pt: "maior que zero", source_pt: "Tabela 5.1, p. 57" }],
      reference_observables: [], actions: { analyze: true, prepare: true, alter: true, simulate: false }, executor_available: true };
    vi.spyOn(api, "experiment").mockResolvedValue(exp);
    vi.spyOn(api, "compatibility").mockResolvedValue(compat);
    const { container } = at("/experimentos/EXP-1/alterar", "/experimentos/:id/alterar", <ScenarioPage />);
    await waitFor(() => expect(screen.getByText("Condições que podem ser alteradas")).toBeTruthy());
    expect(screen.getAllByText("Velocidade do ar").length).toBeGreaterThan(0);
    expect(screen.getByText(/Tabela 5.1, p. 57/)).toBeTruthy();
    expect(screen.getByText(/Este experimento ainda não pode ser simulado no FDS/)).toBeTruthy();
    const text = container.textContent ?? "";
    expect(text).not.toMatch(/queimador|HRRPUA|fuligem/i);
    // o resultado observado aparece só em "Não editáveis" (sem caixa de seleção)
    expect(screen.getAllByRole("checkbox").length).toBe(1);
    expect(screen.getByText("Velocidade de propagação")).toBeTruthy();
  });
});

describe("S07 — vídeo permanece disponível", () => {
  it("mostra o player com o vídeo real da execução concluída e a duração em tempo real", async () => {
    const run = baseRun({ state: "COMPLETED", artifacts: [
      { kind: "VIDEO_MP4", name: "result.mp4", sha256: "b".repeat(64), size_bytes: 25000, meta: { frames: 101, fps: 10, duration_s: 10.1, codec: "h264/yuv420p", simulated_time_s: 10 } },
      { kind: "FRAME_PNG", name: "poster.png", sha256: "c".repeat(64), size_bytes: 3000, meta: {} }] });
    vi.spyOn(api, "run").mockResolvedValue(run);
    vi.spyOn(api, "runs").mockResolvedValue([run]);
    const { container } = at("/execucoes/RUN-1", "/execucoes/:runId", <Result />);
    await waitFor(() => expect(container.querySelector("video")).toBeTruthy());
    const v = container.querySelector("video") as HTMLVideoElement;
    expect(v.getAttribute("src")).toBe("/api/simulations/RUN-1/artifacts/result.mp4");
    expect(v.getAttribute("poster")).toBe("/api/simulations/RUN-1/artifacts/poster.png");
    expect(screen.getByRole("button", { name: "0,25×" })).toBeTruthy();
    expect(screen.getByText(/nenhum quadro foi interpolado/)).toBeTruthy();
  });
  it("sem vídeo real, diz isso e não exibe animação substituta", async () => {
    const run = baseRun({ state: "FAILED", failure_reason: "O Smokeview não produziu quadros; nenhum vídeo foi gerado." });
    vi.spyOn(api, "run").mockResolvedValue(run);
    vi.spyOn(api, "runs").mockResolvedValue([run]);
    const { container } = at("/execucoes/RUN-1", "/execucoes/:runId", <Result />);
    await waitFor(() => expect(screen.getByText(/Não há vídeo real/)).toBeTruthy());
    expect(container.querySelector("video")).toBeNull();
  });
});
