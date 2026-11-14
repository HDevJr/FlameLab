import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";
import { ApiError } from "./api";
import type { Provenance } from "./api";

export type Tone = "ok" | "warn" | "bad" | "info" | "muted";

export function Badge({ tone = "muted", children, title }: { tone?: Tone; children: ReactNode; title?: string }) {
  return <span className={`badge ${tone}`} title={title}>{children}</span>;
}

/** Distingue dados reais, em revisão, de teste e demonstrativos (exigência do protótipo). */
export function DataKind({ kind }: { kind: "REAL" | "REVISAO" | "TESTE" | "DEMO" }) {
  const map = {
    REAL: ["ok", "Dado real"], REVISAO: ["warn", "Em revisão"], TESTE: ["info", "Teste de integração"], DEMO: ["bad", "Demonstrativo"],
  } as const;
  return <Badge tone={map[kind][0]}>{map[kind][1]}</Badge>;
}

export function Layout({ children }: { children: ReactNode }) {
  return (
    <>
      <header className="top">
        <Link to="/" className="brand">🔥 FlameLab <small>protótipo navegável</small></Link>
        <nav>
          <NavLink to="/" end>Biblioteca</NavLink>
          <NavLink to="/importar">Importar artigo</NavLink>
          <NavLink to="/execucoes">Execuções</NavLink>
        </nav>
      </header>
      <main>{children}</main>
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

export function Provenance({ p }: { p: Provenance }) {
  const tone = p.state === "VERIFIED" ? "ok" : p.state === "MISMATCH" ? "bad" : p.state === "CANDIDATE" ? "warn" : "muted";
  return <Badge tone={tone} title={p.reasons_pt.join(" ")}>{p.label_pt}</Badge>;
}

export function Steps({ steps }: { steps: { key: string; label: string; state: string; detail?: string | null }[] }) {
  const icon: Record<string, string> = { DONE: "✔", RUNNING: "⏳", FAILED: "✖", SKIPPED: "⤼", PENDING: "○" };
  return (
    <ol className="steps">
      {steps.map((s) => (
        <li key={s.key} className={s.state.toLowerCase()}>
          <span className="ico">{icon[s.state] ?? "○"}</span>
          <div><strong>{s.label}</strong> <small className="muted">{s.state === "SKIPPED" ? "não executada" : s.state === "PENDING" ? "pendente" : s.state === "RUNNING" ? "em andamento" : s.state === "FAILED" ? "falhou" : "concluída"}</small>
            {s.detail ? <div className="detail">{s.detail}</div> : null}</div>
        </li>
      ))}
    </ol>
  );
}
