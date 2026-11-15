// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Step } from "./api";
import { Layout, StepList } from "./components";
import VideoPlayer from "./Player";

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

