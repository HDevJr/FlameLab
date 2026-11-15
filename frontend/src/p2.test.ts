import { describe, expect, it } from "vitest";
import type { Experiment, Parameter } from "./api";
import { compareExperiments } from "./compare";
import { experimentMarkdown } from "./report";
import { searchExperiments } from "./search";

const par = (parameter: string, value: number | string, unit: string | null, si: [number, string] | null = null, o: Partial<Parameter> = {}): Parameter => ({
  record_id: "R-" + parameter, parameter, label_pt: parameter.replace("_", " "), role: "CONDICAO", nature: "OBSERVADO", status: "CONFERIDO_FONTE",
  original: { value, unit }, normalized: si ? { value: si[0], unit: si[1] } : null, evidence: [{ page_pdf: 65, page_printed: 57, quote: "Initial O2 22.2", locator_pt: "Tabela 5.1" }], caveats_pt: [], ...o,
} as Parameter);
const exp = (id: string, doc: string, parameters: Parameter[], gaps: Experiment["gaps"] = []) => ({ experiment_id: id, label: id, document_id: doc, document_title: doc, parameters, gaps } as unknown as Experiment);
const gap = { gap_id: "G1", parameter: "ambient_pressure", label_pt: "Pressão", explanation_pt: "Nenhuma pressão informada.", purpose_blocked: ["FDS_REPRODUCTION"] } as Experiment["gaps"][number];

describe("relatório exportado", () => {
  const md = experimentMarkdown(exp("M1", "D", [par("thickness", 1, "mm", [0.001, "m"]), par("rate", 0.071, "mm/s", null, { role: "OBSERVAVEL" })], [gap]), { datasetVersion: "sha256:abc", generatedAt: "2026-11-15T00:00:00Z" });
  it("traz versão do dataset, unidade, origem e a lacuna sem estimativa", () => {
    expect(md).toContain("sha256:abc"); expect(md).toContain("1 mm"); expect(md).toContain("Tabela 5.1");
    expect(md).toContain("AUSENTE NA FONTE"); expect(md).toContain("Pressão"); expect(md).toMatch(/endossado pela NASA/);
  });
  it("separa condições de resultados", () => { expect(md.indexOf("Condições de entrada")).toBeLessThan(md.indexOf("Resultados observados")); });
});

describe("comparação", () => {
  it("mesma grandeza em unidades diferentes mas igual em SI não é diferença", () => {
    const c = compareExperiments(exp("A", "D1", [par("w", 2.2, "cm", [0.022, "m"])]), exp("B", "D1", [par("w", 22, "mm", [0.022, "m"])]));
    expect(c.rows[0].differs).toBe(false); expect(c.differing).toBe(0);
  });
  it("valores diferentes e parâmetro só de um lado são sinalizados; documentos distintos geram aviso", () => {
    const c = compareExperiments(exp("A", "D1", [par("w", 2.2, "cm", [0.022, "m"]), par("x", 1, null)]), exp("B", "D2", [par("w", 3, "cm", [0.03, "m"])]));
    expect(c.differing).toBe(1); expect(c.onlyA).toBe(1); expect(c.warnings.join(" ")).toMatch(/documentos diferentes/);
  });
  it("unidades normalizadas incompatíveis não são comparadas numericamente", () => {
    const c = compareExperiments(exp("A", "D", [par("t", 1, "s", [1, "s"])]), exp("B", "D", [par("t", 1, "m", [1, "m"])]));
    expect(c.rows[0].note).toMatch(/não é possível/);
  });
});

describe("busca", () => {
  const list = [exp("M1", "D", [par("o2_initial", 22.2, "vol%"), par("thickness", 1, "mm")], [gap])];
  it("acha por nome e explica o que casou", () => {
    const h = searchExperiments(list, "oxigênio O2 inicial o2_initial");
    expect(h[0].title).toMatch(/o2/); expect(h[0].why.join(" ")).toMatch(/nome/);
  });
  it("lacunas aparecem como lacuna; sem termo, sem resultado; sem acento também casa", () => {
    expect(searchExperiments(list, "pressao")[0].kind).toBe("Lacuna");
    expect(searchExperiments(list, "   ")).toEqual([]);
  });
});
