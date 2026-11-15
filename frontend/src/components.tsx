import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { ApiError, type SystemStatus } from "./api";
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

/** Barra superior (desktop): estado da API e do assistente. Saúde da API não implica validade científica. */
export function StatusBar() {
  const [st, setSt] = useState<SystemStatus | null | "offline">(null);
  useEffect(() => {
    let alive = true;
    const load = () => api.status().then((v) => alive && setSt(v)).catch(() => alive && setSt("offline"));
    load();
    const t = setInterval(load, 30000);
    return () => { alive = false; clearInterval(t); };
  }, []);
  const mode = st && st !== "offline" ? st.assistant.mode : null;
  const modeText = { off: "IA desligada", cache: "IA em cache", live: "IA ao vivo" } as const;
  return (
    <div className="statusbar" role="status" aria-label="Estado do sistema">
      {st === null && <span className="muted">Verificando servidor…</span>}
      {st === "offline" && <Badge tone="bad">Servidor indisponível</Badge>}
      {st && st !== "offline" && (
        <>
          <Badge tone="ok">API online</Badge>
          <Badge tone={mode === "live" ? "info" : mode === "cache" ? "warn" : "muted"} title="Modo do assistente científico">{modeText[mode!]}</Badge>
          {st.assistant.provider !== "none" && <span className="muted">{st.assistant.provider}{st.assistant.model ? ` · ${st.assistant.model}` : ""}{mode === "live" && !st.assistant.live_ready ? " · chave ausente" : ""}</span>}
          {st.dataset_version && <span className="muted" title={st.dataset_version}>dataset <code>{st.dataset_version.slice(7, 15)}</code></span>}
        </>
      )}
    </div>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  const menuBtn = useRef<HTMLButtonElement>(null);
  useEffect(() => { setOpen(false); }, [pathname]);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") { setOpen(false); menuBtn.current?.focus(); } };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);
  return (
    <div className={`shell ${open ? "nav-open" : ""}`}>
      <div className="topbar">
        <button type="button" ref={menuBtn} className="menu-btn" aria-label="Abrir menu" aria-expanded={open} aria-controls="sidebar" onClick={() => setOpen((v) => !v)}>☰</button>
        <Link to="/" className="brand"><img src="/logo-mark.webp" alt="" width="34" height="32" />FlameLab</Link>
      </div>
      <aside className="side" id="sidebar">
        <Link to="/" className="brand"><img src="/logo-mark.webp" alt="" width="38" height="36" /><span>FlameLab<small>Combustão em microgravidade</small></span></Link>
        <nav aria-label="Navegação principal">
          <span className="nav-label">Biblioteca</span>
          <NavLink to="/" end>Experimentos NASA</NavLink>
          <NavLink to="/importar">Importar artigo</NavLink>
          <span className="nav-label">Ferramentas</span>
          <NavLink to="/assistente">Assistente científico</NavLink>
          <NavLink to="/validacao-fds">Validação FDS</NavLink>
          <NavLink to="/demonstracao-fds">Demonstração FDS</NavLink>
          <NavLink to="/execucoes">Execuções</NavLink>
          <NavLink to="/auditoria">Auditoria</NavLink>
        </nav>
        <p className="side-foot"><strong>Projeto independente</strong>Desenvolvido para o NASA Space Apps Challenge. Não é endossado pela NASA.</p>
      </aside>
      {open && <button type="button" className="scrim" aria-label="Fechar menu" onClick={() => { setOpen(false); menuBtn.current?.focus(); }} />}
      <div className="content">
        <StatusBar />
        <main><StaleBackendBanner />{children}</main>
        <footer>
          FlameLab não é produto oficial nem endossado pela NASA ou pelo NIST. Valores marcados “não revisado” não são
          dados conferidos. Simulações exibidas aqui são hipóteses computacionais, não resultados experimentais.
        </footer>
      </div>
    </div>
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
  if (state.loading && !state.data) return <p className="muted" role="status" aria-live="polite">Carregando…</p>;
  if (state.error) return <ErrorBox error={state.error} onRetry={state.reload} />;
  return state.data ? <>{children(state.data)}</> : null;
}

/** Estado vazio explicativo: diz o que falta e como o dado passa a existir (nunca uma tela em branco). */
export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return <div className="empty-state" role="status"><strong>{title}</strong>{children && <p className="muted">{children}</p>}</div>;
}

export function ErrorBox({ error, onRetry }: { error: { message: string; code?: string }; onRetry?: () => void }) {
  const offline = error.code === "BACKEND_UNREACHABLE";
  return (
    <div className="box bad" role="alert">
      <strong>{offline ? "Servidor local indisponível." : "Não foi possível concluir."}</strong> {error.message}{error.code ? <small> ({error.code})</small> : null}
      {offline && <p className="detail" style={{ color: "inherit" }}>Nenhum dado foi alterado. Inicie o backend e tente novamente.</p>}
      {onRetry && <p><button onClick={onRetry}>Tentar novamente</button></p>}
    </div>
  );
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
