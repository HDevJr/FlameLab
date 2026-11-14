import { describe, expect, it } from "vitest";
import type { Parameter } from "./api";
import { formatValue, groupByRole, isTerminal, pathPoints, validateChange } from "./lib";

const p = (role: Parameter["role"], value: number | null, unit: string | null): Parameter => ({
  record_id: "x", parameter: "x", label_pt: "x", role, nature: "OBSERVADO", status: "EXTRAIDO_NAO_REVISADO",
  original: value === null ? null : { value, unit }, normalized: null, evidence: [], caveats_pt: [],
});

describe("lib", () => {
  it("separa condições de resultados observados", () => {
    const g = groupByRole([p("CONDICAO", 1, "mm"), p("OBSERVAVEL", 2, "mm/s"), p("METADADO", null, null)]);
    expect([g.conditions.length, g.observed.length, g.metadata.length]).toEqual([1, 1, 1]);
  });
  it("formata valor com unidade e traço para ausente", () => {
    expect(formatValue(p("CONDICAO", 9, "cm/s"))).toBe("9 cm/s");
    expect(formatValue(p("CONDICAO", null, null))).toBe("—");
  });
  it("valida faixa", () => {
    expect(validateChange(500, 250, 2000, "kW/m²")).toBeNull();
    expect(validateChange(9999, 250, 2000, "kW/m²")).toContain("Fora da faixa");
    expect(validateChange(NaN, 0, 1, "s")).toContain("número");
  });
  it("estados terminais", () => {
    expect(["COMPLETED", "FAILED", "BLOCKED"].every(isTerminal)).toBe(true);
    expect(isTerminal("RUNNING_FDS")).toBe(false);
  });
  it("gera caminho de gráfico", () => {
    expect(pathPoints([[0, 0], [1, 1]], 100, 50, 1, 1)).toBe("M0.0,50.0 L100.0,0.0");
    expect(pathPoints([], 100, 50, 1, 1)).toBe("");
  });
});
