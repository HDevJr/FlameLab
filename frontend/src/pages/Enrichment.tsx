import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, api, type Enrichment as E } from "../api";
import { Async, Badge, ErrorBox, useLoad } from "../components";
import { MATCH_LABEL, render } from "../lib";

/** S03 — Enriquecimento NASA: por que cada fonte foi (ou não) considerada relacionada. */
export default function Enrichment() {
  const { id = "" } = useParams();
  const doc = useLoad(() => api.document(id), [id]);
  const saved = useLoad<E | null>(() => api.enrichment(id).catch((e: ApiError) => { if (e.code === "ENRICHMENT_NOT_RUN") return null; throw e; }), [id]);
  const [fresh, setFresh] = useState<E | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ApiError | null>(null);
  const report = fresh ?? saved.data;

  async function run() {
    setBusy(true); setErr(null);
    try { setFresh(await api.runEnrichment(id)); } catch (e) { setErr(e as ApiError); } finally { setBusy(false); }
  }

  return (
    <>
      <div className="crumbs"><Link to="/">Biblioteca</Link> › Fontes NASA</div>
      <Async state={doc}>{(d) => (
        <>
          <h1>{d.title}</h1>
          <p className="muted">Fluxo: artigo → NTRS → investigação PSI → TechPort. A consulta é opcional; valores de outra fonte <strong>nunca substituem</strong> os do artigo.</p>
          <div className="row"><button className="primary" disabled={busy} onClick={run}>{busy ? "Consultando…" : report ? "Consultar novamente" : "Consultar fontes NASA"}</button>
            {d.experiments[0] && <Link className="btn" to={`/experimentos/${d.experiments[0].experiment_id}`}>Continuar para revisão</Link>}</div>
        </>
      )}</Async>
      {err && <ErrorBox error={err} />}
      {!report && !saved.loading && <div className="box info">O enriquecimento ainda não foi executado para este documento. Você pode prosseguir sem ele.</div>}
      {report && (
        <>
          <div className="box info">Executado em {report.generated_at} · modo <strong>{report.mode === "ONLINE" ? "online (APIs NASA)" : report.mode === "FIXTURE" ? "fixture (respostas gravadas)" : report.mode}</strong> · registros promovidos a “conferido”: <strong>{report.promoted_records}</strong></div>
          {report.warnings_pt.map((w) => <div className="box warn" key={w}>{w}</div>)}
          <h2>Fontes localizadas</h2>
          <div className="grid">{report.matches.map((m) => {
            const l = MATCH_LABEL[m.state] ?? { text: m.state, tone: "muted" as const };
            return (
              <div className="card" key={m.source}>
                <div className="row"><strong>{m.source}</strong><Badge tone={l.tone}>{l.text}</Badge></div>
                {m.title && <p>{m.title}</p>}
                {m.source_record_id && <p><small className="muted">Registro: </small>{m.source_url ? <a href={m.source_url} target="_blank" rel="noreferrer">{m.source_record_id}</a> : m.source_record_id}{m.score != null && <small className="muted"> · semelhança {m.score}</small>}</p>}
                <h3>Por que?</h3>
                <ul>{m.reasons_pt.map((r) => <li key={r}>{r}</li>)}</ul>
                {m.note_pt && <p className="detail">{m.note_pt}</p>}
                {m.rejected_candidates.length > 0 && <details><summary className="detail">Candidatos descartados ({m.rejected_candidates.length})</summary>
                  <ul>{m.rejected_candidates.map((c) => <li key={String(c.id)}><small>{c.title} — {c.score}</small></li>)}</ul></details>}
              </div>
            );
          })}</div>
          <h2>Comparação por campo</h2>
          {report.records.length === 0 ? <p className="muted">Nenhuma fonte complementar respondeu; o processamento segue com os dados do artigo.</p> : (
            <table><thead><tr><th>Campo</th><th>Original (artigo)</th><th>Complementar</th><th>Estado</th><th>Decisão</th></tr></thead><tbody>
              {report.records.filter((r) => r.scope === "DOCUMENT_METADATA").map((r) => {
                const l = MATCH_LABEL[r.state] ?? { text: r.state, tone: "muted" as const };
                return <tr key={r.field}><td>{r.label_pt}</td><td>{render(r.original_value)} <small className="muted">{r.original_source}</small></td>
                  <td>{render(r.complementary_value).slice(0, 220)} <small className="muted">{r.complementary_source} {r.complementary_source_id}</small></td>
                  <td><Badge tone={l.tone}>{l.text}</Badge>{r.divergence_pt && <div className="detail">Divergência: {r.divergence_pt}</div>}</td>
                  <td><small>{r.curation_decision}</small></td></tr>;
              })}
            </tbody></table>
          )}
          <h2>Documentos possivelmente relacionados</h2>
          {report.related_documents.length === 0 ? <p className="muted">Nenhum.</p> : <ul>{report.related_documents.map((r) => <li key={r.ntrs_id}><a href={r.url} target="_blank" rel="noreferrer">{r.title}</a> <small className="muted">NTRS {r.ntrs_id} — {r.note_pt}</small></li>)}</ul>}
          <h2>Operações de API executadas</h2>
          <table><thead><tr><th>Fonte</th><th>Modo</th><th>HTTP</th><th>URL</th></tr></thead><tbody>
            {report.operations.map((o, i) => <tr key={i}><td>{o.source}</td><td>{o.mode}</td><td>{o.error ?? o.http_status}</td><td><small>{o.url.slice(0, 120)}</small></td></tr>)}
          </tbody></table>
        </>
      )}
    </>
  );
}
