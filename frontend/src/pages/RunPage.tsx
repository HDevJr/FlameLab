import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError, api, type Run } from "../api";
import { Async, Badge, DataKind, ErrorBox, useLoad } from "../components";
import { RUN_STEPS, RUN_STEP_LABEL, isTerminal } from "../lib";

export function Pipeline({ run }: { run: Run }) {
  const idx = RUN_STEPS.indexOf(run.state as (typeof RUN_STEPS)[number]);
  return (
    <div className="pipeline">
      {RUN_STEPS.map((s, i) => <span key={s} className={run.state === s ? "on" : idx > i || run.state === "COMPLETED" ? "past" : ""}>{RUN_STEP_LABEL[s]}</span>)}
      {(run.state === "FAILED" || run.state === "BLOCKED") && <span className="on" style={{ background: "var(--bad)" }}>{RUN_STEP_LABEL[run.state]}</span>}
    </div>
  );
}

/** S06 — Execução. Mostra o estado real da tarefa; não há animação simulada. */
export default function RunPage() {
  const { scenarioId = "" } = useParams();
  const nav = useNavigate();
  const sc = useLoad(() => api.scenario(scenarioId), [scenarioId]);
  const status = useLoad(api.simStatus, []);
  const [run, setRun] = useState<Run | null>(null);
  const [err, setErr] = useState<ApiError | null>(null);

  useEffect(() => {
    if (!run || isTerminal(run.state)) return;
    const t = setInterval(async () => { try { setRun(await api.run(run.run_id)); } catch { /* repete */ } }, 1500);
    return () => clearInterval(t);
  }, [run]);

  async function start() {
    setErr(null);
    try { setRun(await api.submit(scenarioId)); } catch (e) { setErr(e as ApiError); }
  }

  return (
    <Async state={sc}>{(s) => (
      <>
        <div className="crumbs"><Link to="/">Biblioteca</Link> › Execução</div>
        <div className="row"><h1 className="grow">{s.title_pt}</h1><DataKind kind="TESTE" /><Badge tone={s.kind === "DERIVED" ? "warn" : "muted"}>{s.kind === "DERIVED" ? "cenário derivado" : "caso-base"}</Badge></div>
        <p className="muted">{s.note_pt}</p>
        <div className="card">
          <h3>Parâmetros</h3>
          <table><tbody>{Object.entries(s.values).map(([k, v]) => {
            const ch = s.changes.find((c) => c.name === k);
            return <tr key={k}><td>{k}</td><td>{ch ? <><s className="muted">{ch.from_value}</s> → <strong>{ch.to_value}</strong> {ch.unit}</> : v}</td></tr>;
          })}</tbody></table>
        </div>
        <Async state={status}>{(st) => (
          <div className="box info">Executor: <strong>{st.executor}</strong> — {st.available ? "disponível" : `indisponível (${st.detail})`}
            {st.versions && <div className="detail">FDS {st.versions.fds} · Smokeview {st.versions.smokeview} · FFmpeg {st.versions.ffmpeg}</div>}
            {st.demo && <div><strong>Executor demonstrativo: nenhum cálculo real.</strong></div>}</div>
        )}</Async>
        {!s.executable && <div className="box bad">Este cenário não pode ser executado: {s.blocked_reasons_pt.join(" ")}</div>}
        {!run && <div className="row"><button className="primary" disabled={!s.executable || !status.data?.available} onClick={start}>Iniciar simulação</button>
          <small className="muted">O servidor gera o arquivo .fds a partir destes parâmetros e o executa em um processo isolado.</small></div>}
        {err && <ErrorBox error={err} />}
        {run && (
          <div className="card">
            <h3>Execução <code>{run.run_id}</code></h3>
            <Pipeline run={run} />
            {run.state === "RUNNING_FDS" && <p className="detail">O cálculo pode levar vários minutos (referência: 5 s simulados ≈ 1 min nesta máquina).</p>}
            {run.failure_reason && <div className="box bad">{run.failure_reason}</div>}
            {run.state === "COMPLETED" && <button className="primary" onClick={() => nav(`/execucoes/${run.run_id}`)}>Ver resultado</button>}
          </div>
        )}
      </>
    )}</Async>
  );
}
