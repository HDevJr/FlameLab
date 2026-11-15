// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, type Experiment, type FieldComparison, type Parameter, type ReviewPreview } from "./api";
import { highlightSegments } from "./lib";
import ReviewPanel, { ReviewError } from "./ReviewPanel";

afterEach(() => { cleanup(); vi.restoreAllMocks(); localStorage.clear(); });

const DEG = "°C";
const QUOTE = "The temperature was then cycled from 20 to 80 °C in increments of 20 °C.";

const param = (o: Partial<Parameter> = {}): Parameter => ({
  record_id: "DOC-1-E1.initial_temperature", parameter: "initial_temperature", technical_name: "initial_temperature", label_pt: "Temperatura inicial",
  label_source: "GLOSSARIO", role: "CONDICAO", nature: "OBSERVADO", status: "EXTRAIDO_NAO_REVISADO", original: { value: 20, unit: DEG }, normalized: { value: 293.15, unit: "K" },
  unit_info: { raw: DEG, canonical: "degC", display: DEG, dimension_pt: "temperatura", supported: true, has_unit: true },
  evidence: [{ page_pdf: 5, page_printed: null, quote: QUOTE, locator_pt: "p. 5 do PDF", literal_check: "PASS" }],
  caveats_pt: [], extraction: { method: "LLM", by: "gemini-3.5-flash-lite" }, events: [],
  semantic_flags: [{ code: "INITIAL_FROM_RANGE", severity: "BLOCKING", title_pt: "O trecho não afirma um valor inicial", detail_pt: "O número 20 aparece como início do intervalo 20 a 80.", terms: ["20", "from", "to"] }],
  ...o,
});
const exp = (p: Parameter): Experiment => ({ experiment_id: "DOC-1-E1", label: "Run A", document_id: "DOC-1", document_title: "Documento", parameters: [p], gaps: [],
  review: { total: 1, reviewed: 0, pending: 1, gaps: 0 }, phenomena: [], origin: "IMPORTED", description: null } as Experiment);

const cmp = (value: FieldComparison["status"] = "MATCH", unit: FieldComparison["status"] = "MATCH", page: FieldComparison["status"] = "MATCH"): FieldComparison[] => [
  { field: "value", label_pt: "Valor", expected: "20", received: "20", status: value, detail_pt: null },
  { field: "unit", label_pt: "Unidade", expected: DEG, received: unit === "MISSING" ? null : DEG, status: unit, detail_pt: unit === "MISSING" ? "o registro está em °C; informe a unidade" : null },
  { field: "page", label_pt: "Página", expected: "5", received: 5, status: page, detail_pt: null },
];
const prev = (o: Partial<ReviewPreview> = {}): ReviewPreview => ({ record_id: "DOC-1-E1.initial_temperature", status: "EXTRAIDO_NAO_REVISADO", comparisons: cmp(), fields_accepted: true,
  field_code: null, field_message_pt: null, failed_fields: [], semantic_flags: [], blocking_flags: [], reviewer_issue: null, accepted: true, ...o });

function open(p: Parameter = param(), preview: ReviewPreview = prev()) {
  vi.spyOn(api, "enrichment").mockRejectedValue(new ApiError(404, "ENRICHMENT_NOT_RUN", "n"));
  vi.spyOn(api, "recordContext").mockResolvedValue({ found: true, page: 5, quote: QUOTE, before: "…four independent fill ports.", after: "The cells were filled.", reason_pt: undefined });
  const previewSpy = vi.spyOn(api, "reviewPreview").mockResolvedValue(preview);
  const onChanged = vi.fn();
  render(<ReviewPanel exp={exp(p)} param={p} onChanged={onChanged} onClose={() => undefined} />);
  return { previewSpy, onChanged };
}
const field = (name: string) => screen.getByLabelText(name) as HTMLInputElement;
const name = (v = "Ana Souza") => fireEvent.change(screen.getByLabelText("Seu nome"), { target: { value: v } });
const declare = () => fireEvent.click(screen.getByLabelText(/Verifiquei a evidência/));

describe("A. extração encontrada", () => {
  it("mostra nome amigável e técnico, valor e unidade separados, tipo e estado", () => {
    open();
    expect(screen.getByRole("heading", { name: "Temperatura inicial" })).toBeTruthy();
    expect(screen.getByText("initial_temperature")).toBeTruthy();
    expect(screen.getByText(/nome traduzido pelo glossário/)).toBeTruthy();
    const kv = document.querySelector("dl.kv") as HTMLElement;
    expect(within(kv).getByText("20")).toBeTruthy();
    expect(within(kv).getByText(DEG)).toBeTruthy();
    expect(within(kv).getByText("(temperatura)")).toBeTruthy();
    expect(within(kv).getByText("Extraído · não revisado")).toBeTruthy();
  });
});

describe("B. evidência", () => {
  it("destaca números e termos no trecho, oferece o contexto e o link para a página", async () => {
    open();
    const marks = [...document.querySelectorAll("blockquote mark")].map((m) => m.textContent);
    expect(marks).toContain("20");
    expect(marks).toContain("from");
    expect(screen.getByRole("link", { name: /Abrir o PDF na página 5/ }).getAttribute("href")).toBe("/api/documents/DOC-1/file#page=5");
    await waitFor(() => expect(screen.getByText("Ver contexto da página")).toBeTruthy());
    expect(document.querySelector("p.context")?.textContent).toContain("The cells were filled.");
  });
  it("mostra a ambiguidade científica (intervalo ≠ valor inicial)", () => {
    open();
    expect(screen.getByText(/Ambiguidade científica: O trecho não afirma um valor inicial/)).toBeTruthy();
    expect(screen.getByText(/início do intervalo 20 a 80/)).toBeTruthy();
  });
});

describe("C. conferência assistida (sem redigitar)", () => {
  it("os campos já vêm preenchidos com a extração", () => {
    open();
    expect(field("Valor informado").value).toBe("20");
    expect(field("Unidade informada").value).toBe(DEG);
    expect(field("Página informada").value).toBe("5");
  });
  it("consulta a prévia do servidor e mostra a correspondência por campo", async () => {
    const { previewSpy } = open(param({ semantic_flags: [] }));
    await waitFor(() => expect(previewSpy).toHaveBeenCalled());
    expect(previewSpy).toHaveBeenLastCalledWith("DOC-1-E1.initial_temperature", expect.objectContaining({ observed_value: "20", observed_unit: DEG, observed_page_pdf: 5 }));
    await waitFor(() => expect(screen.getAllByText("Confere").length).toBe(3));
  });
  it("destaca exatamente o campo que diverge (unidade ausente) e explica por quê", async () => {
    open(param({ semantic_flags: [] }), prev({ comparisons: cmp("MATCH", "MISSING"), fields_accepted: false, field_code: "UNIT_MISSING", failed_fields: ["unit"], accepted: false }));
    fireEvent.change(field("Unidade informada"), { target: { value: "" } });
    await waitFor(() => expect(screen.getByText("Falta")).toBeTruthy());
    const failed = document.querySelectorAll("table.cmp tr.failed");
    expect(failed.length).toBe(1);
    expect(failed[0].textContent).toContain("Unidade");
    expect(screen.getByText(/o registro está em °C; informe a unidade/)).toBeTruthy();
    name(); declare();
    expect((screen.getByRole("button", { name: "Confirmar interpretação" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText(/corrija a unidade/)).toBeTruthy();
  });
  it("o botão de confirmar só habilita com nome, declaração e prévia aceita", async () => {
    open(param({ semantic_flags: [] }));
    const btn = () => screen.getByRole("button", { name: "Confirmar interpretação" }) as HTMLButtonElement;
    await waitFor(() => expect(screen.getAllByText("Confere").length).toBe(3));
    expect(btn().disabled).toBe(true);
    name(); expect(btn().disabled).toBe(true);
    declare(); await waitFor(() => expect(btn().disabled).toBe(false));
  });
  it("ambiguidade científica bloqueia a confirmação mesmo com o número conferido", async () => {
    open(param(), prev({ blocking_flags: param().semantic_flags!, accepted: false }));
    name(); declare();
    await waitFor(() => expect(screen.getAllByText("Confere").length).toBe(3));
    expect((screen.getByRole("button", { name: "Confirmar interpretação" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText(/há ambiguidade científica/)).toBeTruthy();
  });
  it("confirmar sem alterar os campos envia os valores extraídos e registra que não foram alterados", async () => {
    open(param({ semantic_flags: [] }));
    const review = vi.spyOn(api, "review").mockResolvedValue({ outcome: "APPROVED", status: "CONFERIDO_FONTE", event: {} as never });
    name(); declare();
    await waitFor(() => expect((screen.getByRole("button", { name: "Confirmar interpretação" }) as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(screen.getByRole("button", { name: "Confirmar interpretação" }));
    await waitFor(() => expect(screen.getByRole("status").textContent).toContain("Conferência registrada"));
    expect(review).toHaveBeenCalledWith("DOC-1-E1.initial_temperature", expect.objectContaining({ action: "CONFIRM", reviewer: "Ana Souza", observed_value: "20", observed_unit: DEG, observed_page_pdf: 5, checked_pdf: true, prefilled_unchanged: true }));
  });
  it("alterar um campo marca que os valores foram editados pelo revisor", async () => {
    open(param({ semantic_flags: [] }));
    const review = vi.spyOn(api, "review").mockResolvedValue({ outcome: "APPROVED", status: "CONFERIDO_FONTE", event: {} as never });
    name(); declare();
    fireEvent.change(field("Valor informado"), { target: { value: "20.0" } });
    await waitFor(() => expect((screen.getByRole("button", { name: "Confirmar interpretação" }) as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(screen.getByRole("button", { name: "Confirmar interpretação" }));
    await waitFor(() => expect(review).toHaveBeenCalled());
    expect(review.mock.calls[0][1]).toMatchObject({ observed_value: "20.0", prefilled_unchanged: false });
  });
});

describe("recusas do servidor", () => {
  it("mostram qual campo divergiu, com a tabela de comparação", async () => {
    open(param({ semantic_flags: [] }));
    const details = { accepted: false, code: "REVIEW_MISMATCH", reason_code: "UNIT_MISSING", failed_fields: ["unit"], comparisons: cmp("MATCH", "MISSING") };
    vi.spyOn(api, "review").mockRejectedValue(new ApiError(422, "UNIT_MISSING", "unidade ausente: ...", details));
    name(); declare();
    await waitFor(() => expect((screen.getByRole("button", { name: "Confirmar interpretação" }) as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(screen.getByRole("button", { name: "Confirmar interpretação" }));
    const alert = await screen.findAllByRole("alert");
    const text = alert.map((a) => a.textContent).join(" ");
    expect(text).toContain("A unidade não foi informada");
    expect(text).toContain("Campos que falharam: unit");
    expect(alert.some((a) => a.querySelector("tr.failed"))).toBe(true);
  });
  it("ambiguidade semântica devolvida pelo servidor aparece junto da explicação", () => {
    render(<ReviewError err={new ApiError(422, "SEMANTIC_AMBIGUITY", "interpretação científica inconclusiva", { accepted: false, code: "REVIEW_MISMATCH", reason_code: "SEMANTIC_AMBIGUITY", failed_fields: [], comparisons: cmp(), semantic_flags: param().semantic_flags })} />);
    expect(screen.getByRole("alert").textContent).toContain("interpretação científica inconclusiva");
    expect(screen.getByText(/Ambiguidade científica: O trecho não afirma um valor inicial/)).toBeTruthy();
    expect(screen.getByText(/nenhum \(veja a interpretação\)/)).toBeTruthy();  // o número confere: o problema não é nenhum campo
  });
});

describe("D. ações: corrigir, dúvida, divergência", () => {
  it("Corrigir extração envia só o que mudou e informa que o original é preservado", async () => {
    open(param());
    const review = vi.spyOn(api, "review").mockResolvedValue({ outcome: "CORRECTED", status: "EXTRAIDO_NAO_REVISADO", event: {} as never, reopened: false });
    name();
    fireEvent.change(screen.getByLabelText(/Observações/), { target: { value: "O trecho descreve um ciclo" } });
    fireEvent.click(screen.getByRole("button", { name: "Corrigir extração" }));
    fireEvent.change(screen.getByLabelText("Nome do parâmetro"), { target: { value: "Temperatura mínima do ciclo" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar correção" }));
    await waitFor(() => expect(screen.getByRole("status").textContent).toContain("A extração original foi preservada"));
    expect(review).toHaveBeenCalledWith("DOC-1-E1.initial_temperature", expect.objectContaining({
      action: "CORRECT", corrected_label_pt: "Temperatura mínima do ciclo", corrected_value: null, corrected_unit: null, notes: "O trecho descreve um ciclo" }));
  });
  it("dúvida exige observações e divergência exige também o valor", () => {
    open(param());
    name();
    expect((screen.getByRole("button", { name: "Marcar dúvida" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Registrar divergência" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(screen.getByLabelText(/Observações/), { target: { value: "ilegível" } });
    expect((screen.getByRole("button", { name: "Marcar dúvida" }) as HTMLButtonElement).disabled).toBe(false);
    expect((screen.getByRole("button", { name: "Registrar divergência" }) as HTMLButtonElement).disabled).toBe(false);
    fireEvent.change(field("Valor informado"), { target: { value: "" } });
    expect((screen.getByRole("button", { name: "Registrar divergência" }) as HTMLButtonElement).disabled).toBe(true);
  });
  it("registro do dataset curado não oferece correção pela interface", () => {
    const p = param({ semantic_flags: [] });
    vi.spyOn(api, "enrichment").mockRejectedValue(new ApiError(404, "X", "n"));
    vi.spyOn(api, "recordContext").mockRejectedValue(new ApiError(404, "X", "n"));
    vi.spyOn(api, "reviewPreview").mockResolvedValue(prev());
    render(<ReviewPanel exp={{ ...exp(p), origin: "CURATED" }} param={p} onChanged={() => undefined} onClose={() => undefined} />);
    expect((screen.getByRole("button", { name: "Corrigir extração" }) as HTMLButtonElement).disabled).toBe(true);
  });
  it("valor já conferido não oferece nova aprovação, mas permite corrigir (reabre)", () => {
    const done = param({ status: "CONFERIDO_FONTE", review: { reviewer: "Ana", reviewed_at: "2026-11-15T00:00:00Z", notes: null, checked_document_sha256: "a".repeat(64) } });
    open(done);
    expect(screen.queryByRole("button", { name: "Confirmar interpretação" })).toBeNull();
    expect(screen.getByText(/há ambiguidade científica sinalizada/)).toBeTruthy();
    expect(screen.getByRole("button", { name: /Corrigir extração \(reabre a conferência\)/ })).toBeTruthy();
  });
  it("a trilha mostra o campo que falhou em tentativas recusadas", () => {
    open(param({ events: [{ at: "2026-11-15T01:24:51Z", action: "CONFIRM", outcome: "REFUSED", reviewer: "Junior", notes: null, observed_value: "20.0", observed_unit: null, observed_page_pdf: 5,
      code: "UNIT_MISSING", message: "unidade ausente", comparisons: cmp("MATCH", "MISSING") }] }));
    expect(screen.getByText(/Unidade: esperado °C, informado — \(Falta\)/)).toBeTruthy();
    expect(screen.getByText("recusada")).toBeTruthy();
  });
});

describe("destaque de trechos", () => {
  it("marca ocorrências sem distinguir maiúsculas e escapa caracteres especiais", () => {
    expect(highlightSegments("From 20 to 80 °C (x)", ["from", "20", "(x)"]).filter((s) => s.hit).map((s) => s.text)).toEqual(["From", "20", "(x)"]);
    expect(highlightSegments("abc", [])).toEqual([{ text: "abc", hit: false }]);
    expect(highlightSegments("", ["a"])).toEqual([{ text: "", hit: false }]);
  });
});
