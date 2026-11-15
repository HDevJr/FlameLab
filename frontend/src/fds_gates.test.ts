import { describe, expect, it } from "vitest";
import type { Experiment, Gap, Run, SimStatus } from "./api";
import { blockedForReproduction, fdsGates } from "./fds_gates";

const gap = (parameter: string, state: Gap["coverage_state"] = "ABERTA"): Gap => ({ gap_id: "G-" + parameter, parameter, label_pt: parameter, explanation_pt: "", purpose_blocked: [], origin: "CURADORIA", coverage_state: state });
const exp = (gaps: Gap[]) => ({ gaps } as unknown as Experiment);
const status: SimStatus = { executor: "local", available: true, detail: "", demo: false, versions: { fds: "6.11.1", smokeview: "6.11.2", ffmpeg: "9" }, limits: {} };
const run = (scope: Run["scope"], state = "COMPLETED") => ({ scope, state } as unknown as Run);
const by = (g: ReturnType<typeof fdsGates>, id: string) => g.find((x) => x.id === id)!;

describe("gates FDS G0–G5", () => {
  it("lacunas abertas de geometria, material e comparação bloqueiam G1, G2 e G4", () => {
    const g = fdsGates(exp([gap("duct_geometry"), gap("pmma_pyrolysis_properties"), gap("measurement_uncertainty")]), status, []);
    expect(["G1", "G2", "G4"].map((i) => by(g, i).state)).toEqual(["BLOQUEADO", "BLOQUEADO", "BLOQUEADO"]);
    expect(by(g, "G4").reason).toMatch(/Depende também de G2/);
    expect(blockedForReproduction(g)).toBe(true);
  });
  it("sem lacunas abertas o gate não é liberado automaticamente: aguarda aprovação científica", () => {
    const g = fdsGates(exp([gap("duct_geometry", "COBERTA")]), status, []);
    expect(by(g, "G1").state).toBe("AGUARDANDO APROVAÇÃO CIENTÍFICA"); expect(by(g, "G1").tone).toBe("warn");
  });
  it("execução só do caso genérico não conta como execução do experimento", () => {
    const g = fdsGates(exp([]), status, [run("DEMO")]);
    expect(by(g, "G3").state).toBe("SÓ CASO GENÉRICO");
    expect(by(fdsGates(exp([]), status, [run("EXPERIMENT")]), "G3").state).toBe("EXECUTADO NO EXPERIMENTO");
  });
  it("executor indisponível → G0 indisponível; G5 é futuro", () => {
    const g = fdsGates(exp([]), { ...status, available: false, detail: "FDS não encontrado" }, []);
    expect(by(g, "G0-env").state).toBe("INDISPONÍVEL"); expect(by(g, "G5").state).toBe("FUTURO");
  });
});
