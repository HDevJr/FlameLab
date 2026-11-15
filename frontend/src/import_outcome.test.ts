import { describe, expect, it } from "vitest";
import type { ImportRecord, Step } from "./api";
import { importOutcome } from "./import_outcome";

const step = (key: string, state: Step["state"], o: Partial<Step> = {}): Step => ({ key, label_pt: key, state, summary_pt: null, technical: [], limitation_pt: null, started_at: null, finished_at: null, duration_ms: 1, ...o });

// Forma do registro real de um PDF de 402 páginas importado com a IA desligada.
const rec = (o: Partial<ImportRecord> = {}): ImportRecord => ({
  import_id: "IMP-x", filename: "a.pdf", sha256: "x", size_bytes: 1, status: "DONE",
  steps: [step("READ", "DONE", { limitation_pt: "37 página(s) sem texto não podem ser lidas (sem OCR)." }), step("EXTRACT", "SKIPPED", { limitation_pt: "Nenhuma página foi lida por IA." })],
  document: { document_id: "DOC-x", title: null, page_count: 402, pages_with_text: 365, identifiers: { report_numbers: [], ntrs_ids: [], dois: [] } },
  nasa_provenance: { state: "PENDING", label_pt: "Procedência NASA pendente de verificação", reasons_pt: [], ntrs_id: null },
  experiments: [], warnings_pt: ["Nenhuma página foi lida por IA."],
  coverage: { mode: "NONE", total_pages: 402, processed_ranges: "", not_processed_ranges: "", without_text_ranges: "", reasons_pt: ["IA desligada ou não configurada"], summary_pt: "A IA não leu nenhuma página.", pages_processed: [] },
  extraction: null, metrics: { total_ms: 904 }, ...o,
});

describe("resultado da importação", () => {
  it("IA desligada: extração 'não executada' com a causa e o que fazer, sem parecer sucesso", () => {
    const o = importOutcome(rec());
    const ext = o.rows.find((r) => r.key === "EXTRACT")!;
    expect(o.aiOff).toBe(true);
    expect(ext.status).toBe("não executada"); expect(ext.tone).toBe("warn"); expect(ext.action).toMatch(/GEMINI_API_KEY/);
  });
  it("cobertura de páginas: 365 de 402 com texto, 37 sem", () => {
    const read = importOutcome(rec()).rows[0];
    expect(read.detail).toMatch(/365 de 402/); expect(read.detail).toMatch(/37 sem texto/); expect(read.tone).toBe("warn");
  });
  it("origem não verificada sem identificador NASA não vira 'validada'", () => {
    const o = importOutcome(rec()).rows[1];
    expect(o.tone).toBe("muted"); expect(o.detail).toMatch(/não é tratado como publicação NASA validada/);
  });
  it("avisos repetidos entre etapas e registro aparecem uma vez", () => {
    const w = importOutcome(rec()).warnings;
    expect(w.filter((x) => x === "Nenhuma página foi lida por IA.")).toHaveLength(1); expect(w).toHaveLength(2);
  });
  it("extração concluída com experimentos é 'concluída'", () => {
    const o = importOutcome(rec({ steps: [step("READ", "DONE"), step("EXTRACT", "DONE")], experiments: [{} as never], coverage: { mode: "AI_FULL", total_pages: 402, processed_ranges: "1-402", not_processed_ranges: "", without_text_ranges: "", reasons_pt: [], summary_pt: "ok", pages_processed: [] } }));
    expect(o.rows[2].status).toBe("concluída"); expect(o.aiOff).toBe(false);
  });
});
