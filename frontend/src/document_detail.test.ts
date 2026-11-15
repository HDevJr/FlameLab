import { describe, expect, it } from "vitest";
import type { Experiment } from "./api";
import { collectEvidence } from "./pages/DocumentDetail";

const p = (id: string, page: number | null) => ({ record_id: id, label_pt: id, original: { value: 1, unit: "mm" }, evidence: [{ page_pdf: page, page_printed: page ? page - 8 : null, quote: "q", locator_pt: "Tabela 5.1" }] });
const exp = { label: "M1", parameters: [p("a", 65), p("b", 64), p("c", 65), p("d", null)] } as unknown as Experiment;

describe("evidências do documento", () => {
  it("agrupa por página do PDF em ordem crescente e deixa sem página por último", () => {
    const g = collectEvidence([exp]);
    expect([...g.keys()]).toEqual([64, 65, null]);
    expect(g.get(65)!.map((r) => r.parameter)).toEqual(["a", "c"]);
  });
  it("não inventa página: evidência sem página fica em 'null'", () => expect(collectEvidence([exp]).get(null)).toHaveLength(1));
});
