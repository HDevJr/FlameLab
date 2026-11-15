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

/** Linha do tempo do processamento: ordem das etapas, estado, duração real e peso de cada etapa no total. */
export function ImportTimeline({ steps, totalMs }: { steps: Step[]; totalMs: number | null }) {
  const running = steps.some((s) => s.state === "RUNNING");
  const now = useNow(running);
  const ms = steps.map((s) => (s.state === "RUNNING" ? elapsedMs(s.started_at, now) : s.duration_ms));
  const shares = timeShares(ms);
  const slowest = ms.reduce<number>((best, d, i) => ((d ?? 0) > (ms[best] ?? 0) ? i : best), 0);
  return (
    <section aria-label="Linha do tempo do processamento">
      <div className="row"><h3 style={{ margin: 0 }} className="grow">Linha do tempo</h3>
        <small className="muted">{totalMs != null ? `Total ${formatDuration(totalMs)}` : "em andamento"}</small></div>
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
              {s.limitation_pt && s.state !== "PENDING" && <div className="limit">⚠ {s.limitation_pt}</div>}
            </div>
          </li>
        ))}
      </ol>
      {!running && ms[slowest] ? <p className="detail">Etapa mais longa: <strong>{steps[slowest].label_pt}</strong> ({formatDuration(ms[slowest]!)}).</p> : null}
    </section>
  );
}
