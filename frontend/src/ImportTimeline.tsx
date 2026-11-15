import type { Step } from "./api";
import { formatDuration } from "./lib";
import { useNow } from "./components";
import { elapsedMs } from "./lib";

const ICON: Record<Step["state"], string> = { DONE: "✔", RUNNING: "⏳", FAILED: "✖", SKIPPED: "⤼", PENDING: "○" };
const TEXT: Record<Step["state"], string> = { DONE: "concluída", RUNNING: "em andamento", FAILED: "falhou", SKIPPED: "não executada", PENDING: "pendente" };

/** Fração (0–1) do tempo total gasta em cada etapa; usa só durações reais registradas pelo backend. */
export function timeShares(durations: (number | null)[]): number[] {
  const total = durations.reduce<number>((a, d) => a + (d ?? 0), 0);
  return durations.map((d) => (total > 0 && d ? d / total : 0));
}

/**
 * Progresso real do processamento: etapas encerradas (concluída, não executada ou falha) mais a fração dos lotes de IA já
 * concluídos na etapa em andamento. Nada é estimado por tempo; sem lotes informados, a etapa em andamento conta zero.
 */
export function importProgress(steps: Step[], extract?: { completed: number; total: number } | null) {
  const total = steps.length || 1;
  const closed = steps.filter((s) => s.state === "DONE" || s.state === "SKIPPED" || s.state === "FAILED").length;
  const running = steps.find((s) => s.state === "RUNNING");
  const frac = running?.key === "EXTRACT" && extract && extract.total > 0 ? Math.min(1, extract.completed / extract.total) : 0;
  const ratio = Math.min(1, (closed + (running ? frac : 0)) / total);
  const failed = steps.some((s) => s.state === "FAILED");
  const finished = closed === steps.length && steps.length > 0;
  return { percent: Math.round(ratio * 100), closed, total, failed, finished };
}

function Ring({ percent, failed, finished }: { percent: number; failed: boolean; finished: boolean }) {
  const r = 34, c = 2 * Math.PI * r;
  return (
    <div className={`ring ${failed ? "bad" : finished ? "ok" : "run"}`} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent} aria-label="Progresso do processamento">
      <svg viewBox="0 0 80 80" aria-hidden>
        <circle cx="40" cy="40" r={r} className="track" />
        <circle cx="40" cy="40" r={r} className="bar" strokeDasharray={c} strokeDashoffset={c * (1 - percent / 100)} transform="rotate(-90 40 40)" />
      </svg>
      <span className="pct">{percent}%</span>
    </div>
  );
}

/** Linha do tempo do processamento: ordem das etapas, estado, duração real e peso de cada etapa no total. */
export function ImportTimeline({ steps, totalMs, extractProgress }: { steps: Step[]; totalMs: number | null; extractProgress?: { completed: number; total: number } | null }) {
  const running = steps.some((s) => s.state === "RUNNING");
  const now = useNow(running);
  const ms = steps.map((s) => (s.state === "RUNNING" ? elapsedMs(s.started_at, now) : s.duration_ms));
  const shares = timeShares(ms);
  const prog = importProgress(steps, extractProgress);
  const slowest = ms.reduce<number>((best, d, i) => ((d ?? 0) > (ms[best] ?? 0) ? i : best), 0);
  return (
    <section aria-label="Linha do tempo do processamento">
      <div className="tl-head">
        <Ring percent={prog.percent} failed={prog.failed} finished={prog.finished} />
        <div className="grow">
          <h3 style={{ margin: 0 }}>Linha do tempo</h3>
          <div className="detail">{prog.closed} de {prog.total} etapas encerradas{extractProgress && running && steps.find((s) => s.state === "RUNNING")?.key === "EXTRACT" ? ` · lotes de IA: ${extractProgress.completed} de ${extractProgress.total}` : ""}</div>
          <small className="muted">{totalMs != null ? `Total ${formatDuration(totalMs)}` : "em andamento"}</small>
        </div>
      </div>
      <ol className="timeline-steps">
        {steps.map((s, i) => (
          <li key={s.key} className={s.state.toLowerCase()}>
            <span className="dot" aria-hidden>{ICON[s.state]}</span>
            <div className="tl-body">
              <div className="row"><strong className="grow">{s.label_pt}</strong>
                <small className="muted">{TEXT[s.state]}{ms[i] != null && s.state !== "PENDING" ? ` · ${formatDuration(ms[i]!)}` : ""}</small></div>
              {shares[i] > 0 && (
                <div className="tl-bar" role="img" aria-label={`${Math.round(shares[i] * 100)}% do tempo total`}>
                  <span style={{ width: `${Math.max(2, Math.round(shares[i] * 100))}%` }} />
                </div>
              )}
              {s.limitation_pt && s.state !== "PENDING" && (
                <details className="tl-note"><summary>⚠ Ver aviso desta etapa</summary><div className="limit">{s.limitation_pt}</div></details>
              )}
            </div>
          </li>
        ))}
      </ol>
      {!running && ms[slowest] ? <p className="detail">Etapa mais longa: <strong>{steps[slowest].label_pt}</strong> ({formatDuration(ms[slowest]!)}).</p> : null}
    </section>
  );
}
