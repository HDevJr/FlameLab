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

import { REVIEW_ERRORS, elapsedMs, formatClock, formatDuration, playbackRatio, reviewErrorMessage, simulatedTimeAt, SPEEDS, speedLabel } from "./lib";

describe("lib v2.1", () => {
  it("formata durações medidas", () => {
    expect(formatDuration(850)).toBe("850 ms");
    expect(formatDuration(12300)).toBe("12,3 s");
    expect(formatDuration(125000)).toBe("2 min 05 s");
    expect(formatDuration(null)).toBe("—");
  });
  it("calcula tempo decorrido sem inventar progresso", () => {
    expect(elapsedMs("2026-11-14T10:00:00Z", Date.parse("2026-11-14T10:00:05Z"))).toBe(5000);
    expect(elapsedMs(null, 1)).toBeNull();
  });
  it("relógio do player e tempo físico simulado", () => {
    expect(formatClock(65.25)).toBe("1:05.3");
    expect(simulatedTimeAt(5, 10, 20)).toBe(10);
    expect(simulatedTimeAt(5, 0, 20)).toBeNull();
    expect(playbackRatio(10, 10)).toBe(1);
    expect(playbackRatio(1.3, 5)).toBeCloseTo(3.85, 1);
  });
  it("velocidades do player", () => {
    expect([...SPEEDS]).toEqual([0.25, 0.5, 1, 2]);
    expect(speedLabel(0.25)).toBe("0,25×");
  });
  it("traduz códigos de recusa da revisão", () => {
    expect(reviewErrorMessage("REVIEWER_NOT_INDEPENDENT", "x")).toContain("diferente");
    expect(reviewErrorMessage("DESCONHECIDO", "padrão")).toBe("padrão");
    expect(Object.keys(REVIEW_ERRORS).length).toBeGreaterThanOrEqual(10);
  });
});
