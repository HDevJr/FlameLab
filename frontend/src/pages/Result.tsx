import { Link, useParams } from "react-router-dom";
import { api, artifactUrl, type Run } from "../api";
import { Async, Badge, DataKind, useLoad } from "../components";
import { fmtBytes, formatDuration, pathPoints } from "../lib";
import VideoPlayer from "../Player";
import { Pipeline, TimingTable } from "./RunPage";

function Chart({ run, base }: { run: Run; base: Run | null }) {
  const s = run.results.hrr_series;
  if (!s || !s.points.length) return <p className="muted">Sem série de HRR para esta execução.</p>;
  const W = 560, H = 180;
  const xmax = Math.max(...s.points.map((p) => p[0]), ...(base?.results.hrr_series?.points.map((p) => p[0]) ?? [0]));
  const ymax = Math.max(...s.points.map((p) => p[1]), ...(base?.results.hrr_series?.points.map((p) => p[1]) ?? [0])) * 1.1 || 1;
  return (
    <figure style={{ margin: 0 }}>
      <svg viewBox={`-40 -10 ${W + 60} ${H + 40}`} width="100%" role="img" aria-label="Taxa de liberação de calor ao longo do tempo">
        <line x1="0" y1={H} x2={W} y2={H} stroke="var(--line)" /><line x1="0" y1="0" x2="0" y2={H} stroke="var(--line)" />
        {base?.results.hrr_series && <path d={pathPoints(base.results.hrr_series.points, W, H, xmax, ymax)} fill="none" stroke="var(--muted)" strokeWidth="2" strokeDasharray="5 4" />}
        <path d={pathPoints(s.points, W, H, xmax, ymax)} fill="none" stroke="var(--accent)" strokeWidth="2.5" />
        <text x="0" y={H + 18} fontSize="11" fill="var(--muted)">0 s</text><text x={W} y={H + 18} fontSize="11" textAnchor="end" fill="var(--muted)">{xmax.toFixed(1)} s</text>
        <text x="-4" y="10" fontSize="11" textAnchor="end" fill="var(--muted)">{ymax.toFixed(0)}</text><text x="-4" y={H} fontSize="11" textAnchor="end" fill="var(--muted)">0</text>
      </svg>
      <figcaption className="detail">HRR ({s.y_unit}) × tempo (s) — <span style={{ color: "var(--accent)" }}>■</span> esta execução{base && <> · <span>▭ caso-base ({base.run_id})</span></>}. <Badge tone="info">CALCULADO · FDS</Badge></figcaption>
    </figure>
  );
}

/** S07 — Resultado. O vídeo e as curvas são artefatos reais da execução e continuam disponíveis depois do término. */
export default function Result() {
  const { runId = "" } = useParams();
  const run = useLoad(() => api.run(runId), [runId]);
  const all = useLoad(api.runs, []);
  return (
    <Async state={run}>{(r) => {
      const video = r.artifacts.find((a) => a.kind === "VIDEO_MP4");
      const poster = r.artifacts.find((a) => a.kind === "FRAME_PNG");
      const demo = r.scope === "DEMO";
      const base = (all.data ?? []).find((x) => x.run_id !== r.run_id && x.state === "COMPLETED" && x.model_id === r.model_id && x.changes.length === 0 && !x.demo) ?? null;
      const simulated = (video?.meta.simulated_time_s as number | undefined) ?? r.parameters.t_end ?? null;
      return (
        <>
          <div className="crumbs"><Link to="/execucoes">Execuções</Link> › {r.run_id}</div>
          <div className="row"><h1 className="grow">Resultado da simulação</h1><DataKind kind={r.demo ? "DEMO" : "TESTE"} /><Badge tone={r.state === "COMPLETED" ? "ok" : "bad"}>{r.state}</Badge></div>
          <div className="box warn">{demo ? <><strong>Demonstração FDS, independente de qualquer artigo.</strong> </> : null}{r.label_pt}. Este resultado é uma <strong>hipótese computacional</strong>: não é dado experimental NASA e não reproduz o experimento BASS-II.</div>
          <Pipeline run={r} />
          {r.failure_reason && <div className="box bad">{r.failure_reason}</div>}
          {video ? (
            <>
              <VideoPlayer src={artifactUrl(r.run_id, video.name)} poster={poster ? artifactUrl(r.run_id, poster.name) : undefined} simulatedTotal={simulated} />
              <p className="detail">Vídeo gerado pelo Smokeview ({String(video.meta.frames)} quadros a {String(video.meta.fps)} fps) a partir das saídas do FDS, convertido por FFmpeg ({String(video.meta.codec)}). Cada quadro é uma saída real do cálculo; nenhum quadro foi interpolado. SHA-256 <code>{video.sha256.slice(0, 16)}…</code></p>
            </>
          ) : <div className="box info">Não há vídeo real para esta execução. Nenhuma animação substituta é exibida.</div>}
          <h2>Resultados calculados</h2>
          <Chart run={r} base={r.changes.length ? base : null} />
          {r.changes.length > 0 && !base && <p className="detail">Para comparar com o caso-base, execute também o caso sem alterações.</p>}
          {r.results.fds_wall_clock_s != null && <p className="detail">Tempo de cálculo do FDS: {formatDuration(r.results.fds_wall_clock_s * 1000)} · quadros renderizados: {r.results.frame_count}</p>}
          <h2>Tempos medidos desta execução</h2>
          <TimingTable run={r} />
          <h2>Parâmetros e alterações</h2>
          <table><tbody>{Object.entries(r.parameters).map(([k, v]) => { const c = r.changes.find((x) => x.name === k); return <tr key={k}><td>{k}</td><td>{c ? <><s className="muted">{c.from_value}</s> → <strong>{c.to_value}</strong> {c.unit} <Badge tone="warn">alterado</Badge></> : v}</td></tr>; })}</tbody></table>
          <h2>Dados experimentais de referência</h2>
          <p>Comparação quantitativa não disponível para este perfil.</p>
          <p className="muted">O modelo desta execução é um teste de integração e não tem contrapartida experimental NASA. A comparação com valores observados só é válida para um modelo de reprodução aprovado.</p>
          <details className="tech big"><summary>Proveniência e artefatos (técnico)</summary>
            <dl className="kv">
              <dt>Execução</dt><dd>{r.run_id}</dd><dt>Cenário</dt><dd>{r.scenario_id}</dd>
              <dt>SHA-256 do .fds</dt><dd><code>{r.fds_sha256}</code></dd>
              <dt>FDS</dt><dd>{r.fds_version}</dd><dt>Smokeview</dt><dd>{r.smokeview_version}</dd><dt>FFmpeg</dt><dd>{r.ffmpeg_version}</dd>
              <dt>Início → fim</dt><dd>{r.timestamps.QUEUED} → {r.timestamps.COMPLETED ?? r.timestamps[r.state] ?? "—"}</dd>
            </dl>
            <table><thead><tr><th>Tipo</th><th>Arquivo</th><th>Tamanho</th></tr></thead><tbody>
              {r.artifacts.map((a) => <tr key={a.name}><td>{a.kind}</td><td><a href={artifactUrl(r.run_id, a.name)} target="_blank" rel="noreferrer">{a.name}</a></td><td>{fmtBytes(a.size_bytes)}</td></tr>)}
            </tbody></table>
          </details>
        </>
      );
    }}</Async>
  );
}

export function RunList() {
  const runs = useLoad(api.runs, []);
  return (
    <>
      <h1>Execuções</h1>
      <Async state={runs}>{(list) => list.length === 0 ? <p className="muted">Nenhuma execução ainda.</p> : (
        <table><thead><tr><th>Execução</th><th>Estado</th><th>Tipo</th><th>Alterações</th><th>Tempo total</th></tr></thead><tbody>
          {[...list].reverse().map((r) => <tr key={r.run_id}><td><Link to={r.state === "COMPLETED" ? `/execucoes/${r.run_id}` : `/simulacao/${r.scenario_id}`}>{r.run_id}</Link></td>
            <td><Badge tone={r.state === "COMPLETED" ? "ok" : r.state === "FAILED" || r.state === "BLOCKED" ? "bad" : "warn"}>{r.state}</Badge></td>
            <td>{r.demo ? <DataKind kind="DEMO" /> : r.scope === "DEMO" ? <DataKind kind="TESTE" /> : <Badge tone="warn">hipótese sobre experimento</Badge>}</td>
            <td>{r.changes.length ? r.changes.map((c) => `${c.label_pt ?? c.name}: ${c.from_value}→${c.to_value}`).join(", ") : "caso-base"}</td>
            <td>{formatDuration(r.timings_ms?.total)}</td></tr>)}
        </tbody></table>
      )}</Async>
    </>
  );
}
