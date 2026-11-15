// @vitest-environment jsdom
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api, type Compatibility, type Experiment, type UnitInfo } from "./api";
import { StaleBackendBanner, UnitCell } from "./components";
import { REQUIRED_CAPABILITIES, reviewStateView, unitView } from "./lib";
import legacyPayload from "./fixtures/experiment_payload_backend_v2_1.json";
import Review from "./pages/Review";

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

/** Payload REAL (dados do artigo DYLCO importado) como o backend v2.1 o devolve: sem `unit_info`. */
const legacy = legacyPayload as unknown as Experiment;

const compat: Compatibility = {
  experiment_id: legacy.experiment_id, status: "UNSUPPORTED_PHYSICS", reasons_pt: ["Fenômenos fora do alcance do FDS."], missing: [], unreviewed: [],
  editable_conditions: [], editable: [], reference_observables: [], actions: { analyze: true, prepare: true, alter: false, simulate: false }, executor_available: true,
};

function mount(exp: Experiment) {
  vi.spyOn(api, "experiment").mockResolvedValue(exp);
  vi.spyOn(api, "compatibility").mockResolvedValue(compat);
  // GuidedReview busca a jornada ao montar; sem mock a falha de rede (alerta) disputava o getByRole("alert") do teste.
  vi.spyOn(api, "guidedReview").mockImplementation(() => new Promise(() => {}));
  return render(<MemoryRouter initialEntries={["/experimentos/E"]}><Routes><Route path="/experimentos/:id" element={<Review />} /></Routes></MemoryRouter>);
}
const rowOf = (technical: string) => screen.getByText(technical, { selector: "code" }).closest("tr") as HTMLElement;

describe("regressão: a unidade nunca pode sumir da tela (relato de 15/11 — dados reais do DYLCO)", () => {
  it("o payload real do backend antigo não traz unit_info, mas traz original.unit", () => {
    const p = legacy.parameters.find((x) => x.parameter === "initial_temperature")!;
    expect(p.unit_info).toBeUndefined();
    expect(p.original?.unit).toBe("°C");
  });

  it("temperaturas (20, 80, 95, 40) e ângulos (19, 70, 65) aparecem COM a unidade mesmo sem unit_info", async () => {
    mount(legacy);
    await waitFor(() => expect(screen.getByText("initial_temperature")).toBeTruthy());
    const expectations: Record<string, [string, string]> = {
      initial_temperature: ["20", "°C"], peak_temperature_planned: ["80", "°C"], peak_temperature_achieved: ["95", "°C"], temperature: ["40", "degC"],
      uncoated_cells_contact_angle: ["19", "°"], equilibrium_contact_angle: ["70", "deg"], dihedral_angle: ["65", "deg"],
    };
    for (const [technical, [value, unit]] of Object.entries(expectations)) {
      const cells = within(rowOf(technical)).getAllByRole("cell");
      expect(cells[1].textContent).toContain(value);
      expect(cells[2].textContent, `${technical}: coluna Unidade`).toContain(unit); // antes da correção: "—"
      expect(cells[2].textContent).not.toBe("—");
    }
  });

  it("'—' deixa de significar tudo: unidade ausente, não suportada, adimensional e texto têm leituras distintas", async () => {
    const exp = JSON.parse(JSON.stringify(legacy)) as Experiment;
    const byName = (n: string) => exp.parameters.find((p) => p.parameter === n)!;
    byName("test_fluid_code").original = { value: 50350, unit: "adimensional" };  // declaração explícita do registro
    byName("surface_modifier").original = { value: "FC-724", unit: "none" };       // valor textual
    byName("initial_temperature").original = { value: 20, unit: null };            // grandeza física SEM unidade
    byName("temperature").original = { value: 40, unit: "furlong" };               // unidade fora da tabela
    mount(exp);
    await waitFor(() => expect(screen.getByText("initial_temperature")).toBeTruthy());
    const unitOf = (n: string) => within(rowOf(n)).getAllByRole("cell")[2].textContent ?? "";
    expect(unitOf("initial_temperature")).toMatch(/ausente/i);                      // exige unidade e não tem: problema, não "—"
    expect(unitOf("temperature")).toContain("furlong");
    expect(unitOf("test_fluid_code")).toMatch(/sem unidade|adimensional/i);
    expect(unitOf("surface_modifier")).toMatch(/texto|n\/a|não se aplica/i);
  });

  it("avisa quando o servidor está desatualizado em relação à tela (parâmetros sem unit_info)", async () => {
    mount(legacy);
    await waitFor(() => expect(screen.getByText("initial_temperature")).toBeTruthy());
    expect(screen.getByRole("alert").textContent).toMatch(/servidor.*desatualizado|reinicie o backend/i);
  });
});

describe("contrato atual de unidades e versões", () => {
  const base: UnitInfo = { raw: null, canonical: null, display: null, dimension: null, dimension_pt: null, supported: true, has_unit: false };

  it.each([
    ["MISSING", "unidade ausente"], ["DIMENSIONLESS", "adimensional"],
    ["NOT_APPLICABLE", "valor textual"], ["UNSUPPORTED", "furlong (não suportada)"],
  ] as const)("apresenta %s com classificação recebida do backend", (state, text) => {
    const p = { ...legacy.parameters[0], original: { value: 20, unit: state === "UNSUPPORTED" ? "furlong" : null }, unit_info: { ...base, state } };
    render(<UnitCell p={p} />);
    expect(screen.getByText(text, { exact: false })).toBeTruthy();
  });

  it("preserva unidades não classificadas pelo servidor antigo sem inventar suporte", () => {
    const p = { ...legacy.parameters[0], original: { value: 40, unit: "furlong" } };
    expect(unitView(p)).toMatchObject({ text: "furlong", kind: "UNKNOWN", legacy: true });
    expect(unitView({ ...p, original: { value: "20", unit: "°C" } })).toMatchObject({ text: "°C", kind: "UNKNOWN", legacy: true });
    expect(reviewStateView({ ...p, semantic_flags: [] }).tone).toBe("warn");
  });

  it("não declara interpretação confirmada quando o payload antigo não informa o escopo", () => {
    const p = legacy.parameters.find((p) => p.parameter === "peak_temperature_planned")!;
    expect(reviewStateView(p)).toMatchObject({ tone: "warn" });
  });

  it.each([
    [null, true],
    [{ app_version: "old", capabilities: [] }, true],
    [{ app_version: "current", capabilities: REQUIRED_CAPABILITIES }, false],
  ] as const)("detecta ausência ou incompatibilidade de capacidades (%j)", async (version, alert) => {
    vi.spyOn(api, "version").mockResolvedValue(version === null ? null : { ...version, capabilities: [...version.capabilities] });
    render(<StaleBackendBanner />);
    await waitFor(() => expect(api.version).toHaveBeenCalled());
    if (alert) expect(await screen.findByRole("alert")).toBeTruthy();
    else expect(screen.queryByRole("alert")).toBeNull();
  });

  it.each([{}, { app_version: "old" }, { app_version: "old", capabilities: "unit_info" }])("rejeita versão malformada sem falhar a tela (%j)", async (payload) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => payload }));
    expect(await api.version()).toBeNull();
  });
});
