import { describe, expect, it } from "vitest";
import { timeShares } from "./ImportTimeline";

describe("linha do tempo da importação", () => {
  it("fatia o tempo total entre as etapas usando só durações reais", () => {
    const s = timeShares([100, 300, null, 600]);
    expect(s.map((x) => Math.round(x * 100))).toEqual([10, 30, 0, 60]);
  });
  it("sem tempo registrado não inventa porcentagem", () => expect(timeShares([null, null, 0])).toEqual([0, 0, 0]));
});

import type { Step } from "./api";
import { importProgress } from "./ImportTimeline";
const st = (key: string, state: Step["state"]): Step => ({ key, label_pt: key, state, summary_pt: null, technical: [], limitation_pt: null, started_at: null, finished_at: null, duration_ms: 1 });
const ALL = ["RECEIVE", "IDENTIFY", "ORIGIN", "READ", "EXTRACT", "SOURCES", "COMPARE", "REPORT"];

describe("progresso real do anel", () => {
  it("4 de 8 etapas encerradas = 50% e a etapa em andamento sem lotes conta zero", () => {
    const steps = ALL.map((k, i) => st(k, i < 4 ? "DONE" : i === 4 ? "RUNNING" : "PENDING"));
    expect(importProgress(steps).percent).toBe(50);
  });
  it("lotes concluídos entram na fração da extração (2 de 4 lotes = +6%)", () => {
    const steps = ALL.map((k, i) => st(k, i < 4 ? "DONE" : i === 4 ? "RUNNING" : "PENDING"));
    expect(importProgress(steps, { completed: 2, total: 4 }).percent).toBe(56);
  });
  it("tudo encerrado = 100%; falha marca o anel como falha", () => {
    expect(importProgress(ALL.map((k) => st(k, "DONE")))).toMatchObject({ percent: 100, finished: true, failed: false });
    expect(importProgress(ALL.map((k, i) => st(k, i === 4 ? "FAILED" : "DONE"))).failed).toBe(true);
  });
  it("etapa não executada conta como encerrada, mas não vira 'falha'", () => {
    expect(importProgress(ALL.map((k) => st(k, k === "EXTRACT" ? "SKIPPED" : "DONE")))).toMatchObject({ percent: 100, failed: false });
  });
});
