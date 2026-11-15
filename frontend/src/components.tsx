import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";
import { ApiError } from "./api";
import type { Provenance as ProvenanceT, Step } from "./api";
import { GLOSSARY, elapsedMs, formatDuration } from "./lib";

export type Tone = "ok" | "warn" | "bad" | "info" | "muted";

export function Badge({ tone = "muted", children, title }: { tone?: Tone; children: ReactNode; title?: string }) {
  return <span className={`badge ${tone}`} title={title}>{children}</span>;
}

/** Termo técnico com explicação em linguagem simples (abre ao clicar ou passar o mouse). */
export function Term({ k, children }: { k: keyof typeof GLOSSARY | string; children: ReactNode }) {
  const text = GLOSSARY[k];
  if (!text) return <>{children}</>;
  return <abbr className="term" title={text} tabIndex={0}>{children}<span className="q" aria-label={`O que é: ${text}`}>?</span></abbr>;
}

/** Distingue dados reais, em revisão, de teste e demonstrativos (exigência do protótipo). */
export function DataKind({ kind }: { kind: "REAL" | "REVISAO" | "TESTE" | "DEMO" }) {
  const map = {
    REAL: ["ok", "Dado conferido"], REVISAO: ["warn", "Em revisão"], TESTE: ["info", "Teste de integração"], DEMO: ["bad", "Executor simulado (teste)"],
  } as const;
  return <Badge tone={map[kind][0]}>{map[kind][1]}</Badge>;
}

export function Layout({ children }: { children: ReactNode }) {
  return (
    <>
      <header className="top">
        <Link to="/" className="brand">🔥 FlameLab <small>protótipo navegável</small></Link>
        <nav aria-label="Navegação principal">
          <NavLink to="/" end>Experimentos NASA</NavLink>
          <NavLink to="/importar">Importar artigo</NavLink>
          <NavLink to="/demonstracao-fds">Demonstração FDS</NavLink>
          <NavLink to="/execucoes">Execuções</NavLink>
          <NavLink to="/auditoria">Auditoria</NavLink>
        </nav>
      </header>
      <main><StaleBackendBanner />{children}</main>
      <footer>
        FlameLab não é produto oficial nem endossado pela NASA ou pelo NIST. Valores marcados “não revisado” não são
        dados conferidos. Simulações exibidas aqui são hipóteses computacionais, não resultados experimentais.
      </footer>
    </>
  );
}

export function useLoad<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let alive = true;
    setLoading(true);
    fn().then((d) => alive && (setData(d), setError(null)))
      .catch((e: ApiError) => alive && setError(e))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  return { data, error, loading, reload: () => setTick((t) => t + 1) };
}

export function Async<T>({ state, children }: { state: ReturnType<typeof useLoad<T>>; children: (d: T) => ReactNode }) {
  if (state.loading && !state.data) return <p className="muted">Carregando…</p>;
  if (state.error) return <ErrorBox error={state.error} />;
  return state.data ? <>{children(state.data)}</> : null;
}

export function ErrorBox({ error }: { error: { message: string; code?: string } }) {
  return <div className="box bad" role="alert"><strong>Não foi possível concluir.</strong> {error.message}{error.code ? <small> ({error.code})</small> : null}</div>;
}

export function Provenance({ p }: { p: ProvenanceT }) {
  const tone = p.state === "VERIFIED" ? "ok" : p.state === "MISMATCH" ? "bad" : p.state === "CANDIDATE" ? "warn" : "muted";
  return <Badge tone={tone} title={p.reasons_pt.join(" ")}>{p.label_pt}</Badge>;
}

/** Relógio que reavalia a cada segundo enquanto `active` (para tempo decorrido real, sem percentual inventado). */
export function useNow(active: boolean): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [active]);
  return now;
}

const ICON: Record<string, string> = { DONE: "✔", RUNNING: "⏳", FAILED: "✖", SKIPPED: "⤼", PENDING: "○" };
const STATE_TEXT: Record<string, string> = { DONE: "concluída", RUNNING: "em andamento", FAILED: "falhou", SKIPPED: "não executada", PENDING: "pendente" };

/** Etapas do processamento: estado real, resumo, limitação e detalhes técnicos expansíveis. */
export function StepList({ steps }: { steps: Step[] }) {
  const running = steps.some((s) => s.state === "RUNNING");
  const now = useNow(running);
  return (
    <ol className="steps">
      {steps.map((s) => {
        const time = s.state === "RUNNING" ? elapsedMs(s.started_at, now) : s.duration_ms;
        return (
          <li key={s.key} className={s.state.toLowerCase()}>
            <span className="ico" aria-hidden>{ICON[s.state] ?? "○"}</span>
            <div className="grow">
              <div><strong>{s.label_pt}</strong> <small className="muted">{STATE_TEXT[s.state]}{time != null && s.state !== "PENDING" ? ` · ${formatDuration(time)}` : ""}</small></div>
              {s.summary_pt && s.state !== "PENDING" && <div className="detail">{s.summary_pt}</div>}
              {s.limitation_pt && <div className="limit">⚠ {s.limitation_pt}</div>}
              {s.technical.length > 0 && s.state !== "PENDING" && (
                <details className="tech"><summary>Detalhes técnicos</summary><ul>{s.technical.map((t, i) => <li key={i}>{t}</li>)}</ul></details>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

// ---------------------------------------------------------------- v2.3: unidade, prontidão e versão do servidor
import { api, type Parameter, type Readiness } from "./api";
import { READINESS_STATUS, REQUIRED_CAPABILITIES, unitView } from "./lib";

/** Unidade com leitura própria para cada estado (nunca "—" para tudo). */
export function UnitCell({ p }: { p: Parameter }) {
  const u = unitView(p);
  return <span title={u.title}><Badge tone={u.tone}>{u.text}</Badge></span>;
}

/** Cinco dimensões independentes: integridade · revisão · cobertura · compatibilidade FDS · prontidão para execução. */
export function ReadinessPanel({ readiness, experimentId, onResolve }: { readiness: Readiness | undefined; experimentId?:string; onResolve?:()=>void }) {
  if (!readiness) return <p className="muted">Avaliando prontidão…</p>;
  return (
    <ol className="readiness" aria-label="Prontidão em cinco dimensões">
      {readiness.dimensions.map((d, i) => (
        <li key={d.key} className={d.tone}>
          <div className="row"><strong>{i + 1}. {d.label_pt}</strong><Badge tone={d.tone}>{READINESS_STATUS[d.status] ?? d.status}</Badge></div>
          <div className="detail">{d.summary_pt}</div>
          {d.items.length > 0 && <details className="tech"><summary>Detalhes ({d.items.length})</summary><ul>{d.items.map((t, k) => <li key={k}>{t}</li>)}</ul></details>}
          {experimentId && (d.tone!=="ok" || d.key==="execution_readiness") && <div className="readiness-action">
            {d.key==="coverage" && onResolve ? <button onClick={onResolve}>Resolver pendências</button>:
             ["scientific_review","extraction_integrity"].includes(d.key) ? <a className="btn" href="#parametros">Revisar parâmetros</a>:
             <Link className="btn" to={`/experimentos/${experimentId}/preparar`}>{d.key==="execution_readiness" && readiness.can_simulate ? "Preparar execução":"Entender requisitos do modelo"}</Link>}
          </div>}
        </li>
      ))}
    </ol>
  );
}

/** Avisa quando o backend em execução é anterior às telas (ex.: não envia a unidade classificada). */
export function StaleBackendBanner() {
  const [problem, setProblem] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    api.version().then((v) => {
      if (!alive) return;
      if (v === null) setProblem("Não foi possível confirmar a versão do servidor (rota /api/version ausente ou servidor fora do ar).");
      else { const missing = REQUIRED_CAPABILITIES.filter((c) => !v.capabilities.includes(c)); setProblem(missing.length ? `Servidor desatualizado: faltam recursos (${missing.join(", ")}).` : null); }
    });
    return () => { alive = false; };
  }, []);
  if (!problem) return null;
  return <div className="box bad" role="alert"><strong>{problem}</strong> Reinicie o backend para carregar a versão atual: as telas podem exibir dados incompletos (por exemplo, unidades) até lá.</div>;
}
