import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError, api, type Run } from "../api";
import { Async, Badge, DataKind, ErrorBox, Term, useLoad, useNow } from "../components";
import { RUN_STEPS, RUN_STEP_LABEL, elapsedMs, formatDuration, isTerminal } from "../lib";

export function Pipeline({ run }: { run: Run }) {
  const idx = RUN_STEPS.indexOf(run.state as (typeof RUN_STEPS)[number]);
  return (
    <div className="pipeline">
      {RUN_STEPS.map((s, i) => <span key={s} className={run.state === s ? "on" : idx > i || run.state === "COMPLETED" ? "past" : ""}>{RUN_STEP_LABEL[s]}</span>)}
      {(run.state === "FAILED" || run.state === "BLOCKED") && <span className="on" style={{ background: "var(--bad)" }}>{RUN_STEP_LABEL[run.state]}</span>}
    </div>
  );
}

export const TIMING_LABELS: [string, string][] = [
  ["queue_wait", "Espera na fila"], ["preparation", "Preparação do caso (validação e geração do .fds)"], ["fds", "Execução do FDS"],
  ["processing", "Processamento das saídas"], ["smokeview", "Renderização no Smokeview"], ["mp4_encoding", "Codificação do MP4 (FFmpeg)"], ["total", "Total"],
];

export function TimingTable({ run }: { run: Run }) {
  const rows = TIMING_LABELS.filter(([k]) => run.timings_ms[k] != null);
  if (!rows.length) return <p className="detail">Tempos ainda não disponíveis.</p>;
  return <table><tbody>{rows.map(([k, label]) => <tr key={k}><td>{label}</td><td><strong>{formatDuration(run.timings_ms[k])}</strong></td></tr>)}</tbody></table>;
}

/** S06 — Execução. Estado real da tarefa, tempo decorrido e progresso físico real do FDS (quando informado). */
export default function RunPage() {
  const { scenarioId = "" } = useParams();
  const nav = useNavigate();
  const sc = useLoad(() => api.scenario(scenarioId), [scenarioId]);
  const status = useLoad(api.simStatus, []);
  const [run, setRun] = useState<Run | null>(null);
  const [err, setErr] = useState<ApiError | null>(null);
  const active = !!run && !isTerminal(run.state);
  const now = useNow(active);

  // A tela não perde a execução ao navegar: reencontra a execução mais recente deste cenário.
  useEffect(() => {
    api.runs().then((all) => { const mine = all.filter((r) => r.scenario_id === scenarioId); if (mine.length) setRun(mine[mine.length - 1]); }).catch(() => undefined);
  }, [scenarioId]);

  useEffect(() => {
    if (!run || isTerminal(run.state)) return;
    const t = setInterval(async () => { try { setRun(await api.run(run.run_id)); } catch { /* repete */ } }, 1000);
    return () => clearInterval(t);
  }, [run]);

  async function start() {
    setErr(null);
    try { setRun(await api.submit(scenarioId)); } catch (e) { setErr(e as ApiError); }
  }

  return (
    <Async state={sc}>{(s) => {
      const demo = s.scope === "DEMO";
      const elapsed = run && active ? elapsedMs(run.timestamps.QUEUED, now) : null;
      return (
        <>
          <div className="crumbs">{demo ? <Link to="/demonstracao-fds">Demonstração FDS</Link> : <Link to={`/experimentos/${s.experiment_id}`}>Experimento {s.experiment_id}</Link>} › Execução</div>
          <div className="row"><h1 className="grow">{s.title_pt}</h1>
            {demo ? <DataKind kind="TESTE" /> : <Badge tone="warn">Hipótese sobre experimento NASA</Badge>}
            <Badge tone={s.kind === "DERIVED" ? "warn" : "muted"}>{s.kind === "DERIVED" ? "cenário derivado" : "caso-base"}</Badge></div>
          {demo
            ? <div className="box info"><strong>Demonstração FDS:</strong> caso genérico independente de qualquer artigo. Estes parâmetros não pertencem a nenhum experimento NASA. <Term k="demo_fds">Saiba mais</Term></div>
            : <div className="box warn"><strong>Hipótese sobre {s.experiment_id}.</strong> {s.note_pt}</div>}
          {s.hypothesis_pt && <p><strong>Hipótese:</strong> {s.hypothesis_pt}</p>}
          <div className="card">
            <h3>{demo ? "Parâmetros da demonstração" : "Alterações em relação ao experimento"}</h3>
            <table><tbody>{(demo ? Object.entries(s.values).map(([k, v]) => ({ k, label: k, c: s.changes.find((c) => c.name === k), v })) :
              s.changes.map((c) => ({ k: c.name, label: c.label_pt ?? c.name, c, v: c.to_value }))).map(({ k, label, c, v }) => (
              <tr key={k}><td>{label}</td><td>{c ? <><s className="muted">{c.from_value}</s> → <strong>{c.to_value}</strong> {c.unit} {c.base_status === "EXTRAIDO_NAO_REVISADO" && <Badge tone="warn">valor original não revisado</Badge>}</> : v}</td></tr>
            ))}</tbody></table>
          </div>
          <Async state={status}>{(st) => (
            <div className="box info">Executor: <strong>{st.executor}</strong> — {st.available ? "disponível" : `indisponível (${st.detail})`}
              {st.versions && <div className="detail">FDS {st.versions.fds} · Smokeview {st.versions.smokeview} · FFmpeg {st.versions.ffmpeg}</div>}
              {st.demo && <div><strong>Executor demonstrativo: nenhum cálculo real.</strong></div>}</div>
          )}</Async>
          {!s.executable && <div className="box bad"><strong>Este cenário não pode ser executado.</strong> {s.blocked_reasons_pt.join(" ")}<div className="detail">O cenário foi salvo como hipótese. Nenhuma simulação genérica é usada no lugar.</div></div>}
          {!run && <div className="row"><button className="primary" disabled={!s.executable || !status.data?.available} onClick={start}>Iniciar simulação</button>
            <small className="muted">O servidor gera o arquivo .fds a partir destes parâmetros e o executa em um processo isolado.</small></div>}
          {err && <ErrorBox error={err} />}
          {run && (
            <div className="card">
              <h3>Execução <code>{run.run_id}</code></h3>
              <Pipeline run={run} />
              {active && (
                <div className="box info" role="status" aria-live="polite">
                  <strong>{run.state === "RUNNING_FDS" ? "O FDS está executando o cálculo." : `Etapa atual: ${RUN_STEP_LABEL[run.state]}.`}</strong>{" "}
                  Tempo decorrido: <strong>{formatDuration(elapsed)}</strong>.
                  {run.progress ? (
                    <div>
                      <div className="bar" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(run.progress.fraction * 100)}><div style={{ width: `${run.progress.fraction * 100}%` }} /></div>
                      <small>Tempo físico calculado: {run.progress.simulated_time_s.toFixed(2).replace(".", ",")} s de {run.progress.t_end_s} s (informado pelo log do FDS; não é previsão de quando termina).</small>
                    </div>
                  ) : <div><div className="bar indeterminate" aria-label="Progresso indeterminado" /><small>Sem informação confiável de progresso nesta etapa; mostrando apenas o tempo decorrido.</small></div>}
                  <div className="detail">Você pode sair desta tela: a execução continua no servidor e aparece em “Execuções”.</div>
                </div>
              )}
              {run.failure_reason && <div className="box bad">{run.failure_reason}</div>}
              {isTerminal(run.state) && <><h3>Tempos medidos</h3><TimingTable run={run} /></>}
              {run.state === "COMPLETED" && <button className="primary" onClick={() => nav(`/execucoes/${run.run_id}`)}>Ver resultado e vídeo</button>}
            </div>
          )}
        </>
      );
    }}</Async>
  );
}
