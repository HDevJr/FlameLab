// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, type Experiment, type Parameter, type Step } from "./api";
import { Layout, StepList } from "./components";
import VideoPlayer from "./Player";
import ReviewPanel from "./ReviewPanel";

afterEach(() => { cleanup(); vi.restoreAllMocks(); localStorage.clear(); });

beforeEach(() => {
  // jsdom não implementa reprodução de mídia
  Object.defineProperty(HTMLMediaElement.prototype, "play", { configurable: true, value: vi.fn(() => Promise.resolve()) });
  Object.defineProperty(HTMLMediaElement.prototype, "pause", { configurable: true, value: vi.fn() });
});

describe("navegação: experimentos NASA × demonstração FDS", () => {
  it("separa os dois caminhos no menu", () => {
    render(<MemoryRouter><Layout><p /></Layout></MemoryRouter>);
    expect(screen.getByRole("link", { name: "Experimentos NASA" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Demonstração FDS" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Importar artigo" })).toBeTruthy();
  });
});

describe("StepList", () => {
  const step = (o: Partial<Step>): Step => ({ key: "K", label_pt: "Etapa", state: "DONE", summary_pt: "resumo", technical: [], limitation_pt: null, started_at: null, finished_at: null, duration_ms: 1500, ...o });
  it("mostra tempo real, limitação e detalhes técnicos expansíveis", () => {
    render(<StepList steps={[step({ label_pt: "Extraindo", limitation_pt: "Leu 12 de 32 páginas", technical: ["lote 1: páginas 1–12"] }), step({ key: "B", label_pt: "Pendente", state: "PENDING", duration_ms: null })]} />);
    expect(screen.getByText("Leu 12 de 32 páginas", { exact: false })).toBeTruthy();
    expect(screen.getByText("1,5 s", { exact: false })).toBeTruthy();
    expect(screen.getByText("Detalhes técnicos")).toBeTruthy();
    expect(screen.getAllByText("pendente", { exact: false }).length).toBeGreaterThan(0);
  });
});

describe("VideoPlayer", () => {
  const mount = () => {
    const r = render(<VideoPlayer src="/api/x.mp4" simulatedTotal={10} />);
    const video = r.container.querySelector("video") as HTMLVideoElement;
    Object.defineProperty(video, "duration", { configurable: true, value: 10 });
    fireEvent.loadedMetadata(video);
    return video;
  };
  it("tem reproduzir/pausar, reproduzir novamente, linha do tempo e tela cheia", () => {
    mount();
    expect(screen.getByRole("button", { name: "Reproduzir" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Reproduzir novamente" })).toBeTruthy();
    expect(screen.getByLabelText("Linha do tempo")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Tela cheia/ })).toBeTruthy();
  });
  it("oferece 0,25×, 0,5×, 1× e 2× e aplica a velocidade ao vídeo", () => {
    const v = mount();
    for (const label of ["0,25×", "0,5×", "1×", "2×"]) expect(screen.getByRole("button", { name: label })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "0,25×" }));
    expect(v.playbackRate).toBe(0.25);
    fireEvent.click(screen.getByRole("button", { name: "2×" }));
    expect(v.playbackRate).toBe(2);
  });
  it("repetição automática é configurável e lembrada", () => {
    const v = mount();
    const box = screen.getByLabelText("Repetir automaticamente") as HTMLInputElement;
    expect(box.checked).toBe(true);
    expect(v.loop).toBe(true);
    fireEvent.click(box);
    expect(v.loop).toBe(false);
    expect(localStorage.getItem("flamelab.player.loop")).toBe("0");
  });
  it("indica duração e o tempo físico simulado; 1 s de vídeo = 1 s simulado", () => {
    mount();
    expect(screen.getByText("Duração do vídeo:", { exact: false }).textContent).toContain("0:10.0");
    expect(screen.getByText("1 s de vídeo = 1 s de tempo físico simulado", { exact: false })).toBeTruthy();
  });
  it("avisa quando o vídeo não pode ser carregado", () => {
    const r = render(<VideoPlayer src="/api/quebrado.mp4" />);
    fireEvent.error(r.container.querySelector("video") as HTMLVideoElement);
    expect(screen.getByRole("alert").textContent).toContain("não pôde ser carregado");
  });
  it("reproduzir novamente volta ao início", () => {
    const v = mount();
    v.currentTime = 7;
    fireEvent.click(screen.getByRole("button", { name: "Reproduzir novamente" }));
    expect(v.currentTime).toBe(0);
    expect(HTMLMediaElement.prototype.play).toHaveBeenCalled();
  });
});

describe("ReviewPanel", () => {
  const param: Parameter = {
    record_id: "X-E1.width", parameter: "width", label_pt: "Largura", role: "CONDICAO", nature: "OBSERVADO", status: "EXTRAIDO_NAO_REVISADO",
    original: { value: 2.2, unit: "cm" }, normalized: null, caveats_pt: [], extraction: { method: "LLM", by: "modelo-x" },
    evidence: [{ page_pdf: 65, page_printed: 57, quote: "width 2.2 cm", locator_pt: "Tabela 5.1, p. 57", literal_check: "PASS" }], events: [],
  };
  const exp = { experiment_id: "X-E1", label: "Exp", document_id: "DOC-1", document_title: "Documento", parameters: [param], gaps: [], review: { total: 1, reviewed: 0, pending: 1, gaps: 0 }, phenomena: [], origin: "IMPORTED", description: null } as Experiment;
  const open = () => { vi.spyOn(api, "enrichment").mockRejectedValue(new ApiError(404, "ENRICHMENT_NOT_RUN", "n")); return render(<ReviewPanel exp={exp} param={param} onChanged={() => undefined} onClose={() => undefined} />); };

  it("mostra valor, experimento, página e trecho e deixa os campos de leitura vazios", () => {
    open();
    expect(screen.getByText("2.2 cm")).toBeTruthy();
    expect(screen.getByText("(X-E1)")).toBeTruthy();
    expect(screen.getByText("“width 2.2 cm”")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Abrir o PDF na página 65/ }).getAttribute("href")).toBe("/api/documents/DOC-1/file#page=65");
    expect((screen.getByLabelText("Valor lido no PDF") as HTMLInputElement).value).toBe("");
  });
  it("não envia sem nome do revisor; dúvida exige observações", () => {
    open();
    expect((screen.getByRole("button", { name: "Confirmar conferência" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(screen.getByLabelText("Seu nome"), { target: { value: "Ana Souza" } });
    expect((screen.getByRole("button", { name: "Confirmar conferência" }) as HTMLButtonElement).disabled).toBe(false);
    expect((screen.getByRole("button", { name: /Manter pendente/ }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(screen.getByLabelText(/Observações/), { target: { value: "ilegível" } });
    expect((screen.getByRole("button", { name: /Manter pendente/ }) as HTMLButtonElement).disabled).toBe(false);
  });
  it("envia exatamente o que foi lido e traduz a recusa do servidor", async () => {
    open();
    const review = vi.spyOn(api, "review").mockRejectedValue(new ApiError(422, "VALUE_MISMATCH", "diverge"));
    fireEvent.change(screen.getByLabelText("Seu nome"), { target: { value: "Ana Souza" } });
    fireEvent.change(screen.getByLabelText("Valor lido no PDF"), { target: { value: "9" } });
    fireEvent.change(screen.getByLabelText("Unidade lida"), { target: { value: "cm" } });
    fireEvent.change(screen.getByLabelText("Página do PDF"), { target: { value: "65" } });
    fireEvent.click(screen.getByLabelText("Conferi o valor no PDF original."));
    fireEvent.click(screen.getByRole("button", { name: "Confirmar conferência" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("Nada foi aprovado"));
    expect(review).toHaveBeenCalledWith("X-E1.width", expect.objectContaining({ action: "CONFIRM", reviewer: "Ana Souza", observed_value: "9", observed_unit: "cm", observed_page_pdf: 65, checked_pdf: true }));
  });
  it("registra divergência sem prometer alteração do dado", async () => {
    open();
    vi.spyOn(api, "review").mockResolvedValue({ outcome: "RECORDED", status: "EXTRAIDO_NAO_REVISADO", event: {} as never });
    fireEvent.change(screen.getByLabelText("Seu nome"), { target: { value: "Ana Souza" } });
    fireEvent.change(screen.getByLabelText("Valor lido no PDF"), { target: { value: "3" } });
    fireEvent.change(screen.getByLabelText(/Observações/), { target: { value: "PDF mostra 3 cm" } });
    fireEvent.click(screen.getByRole("button", { name: "Registrar divergência" }));
    await waitFor(() => expect(screen.getByRole("status").textContent).toContain("continua pendente e não foi alterado"));
  });
  it("valor já conferido não oferece nova aprovação", () => {
    const done = { ...param, status: "CONFERIDO_FONTE", review: { reviewer: "Ana", reviewed_at: "2026-11-14T00:00:00Z", notes: null, checked_document_sha256: "a".repeat(64) } };
    vi.spyOn(api, "enrichment").mockRejectedValue(new ApiError(404, "X", "n"));
    render(<ReviewPanel exp={exp} param={done} onChanged={() => undefined} onClose={() => undefined} />);
    expect(screen.queryByRole("button", { name: "Confirmar conferência" })).toBeNull();
    expect(screen.getByText("Ana", { exact: false })).toBeTruthy();
  });
});
