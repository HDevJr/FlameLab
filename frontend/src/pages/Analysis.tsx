import { Link, useParams } from "react-router-dom";
import { api, type Analysis as A } from "../api";
import { Async, Badge, Provenance, StepList, Term, useLoad } from "../components";
import { COMPAT_LABEL, GLOSSARY, MATCH_LABEL, formatDuration } from "../lib";

/** Conclusões primeiro; logs e respostas técnicas ficam em áreas expansíveis. */
export function AnalysisSummary({ a, compact = false }: { a: A; compact?: boolean }) {
  const cov = a.coverage;
  return (
    <>
      <div className="card headline">
        <ul className="conclusions">{a.conclusions_pt.map((c) => <li key={c}>{c}</li>)}</ul>
      </div>
      <div className="grid">
        <div className="card">
          <h3><Term k="procedencia">Origem NASA</Term></h3>
          <Provenance p={a.provenance} />
          <p className="detail">{a.provenance.reasons_pt[a.provenance.reasons_pt.length - 1]}</p>
          <small className="muted"><Term k="sha256">SHA-256</Term>: <code>{(a.document.sha256 ?? "—").slice(0, 20)}…</code></small>
        </div>
        <div className="card">
          <h3><Term k="cobertura">Cobertura da leitura</Term></h3>
          <Badge tone={cov.mode === "AI_FULL" || cov.mode === "CURATED" ? "ok" : cov.mode === "AI_PARTIAL" ? "warn" : "muted"}>
            {cov.mode === "AI_FULL" ? "Todas as páginas com texto" : cov.mode === "AI_PARTIAL" ? "Leitura parcial" : cov.mode === "CURATED" ? "Dataset curado" : "Sem leitura por IA"}
          </Badge>
          <p className="detail">{cov.summary_pt}</p>
          {cov.mode !== "CURATED" && cov.mode !== "NONE" && (
            <dl className="kv small"><dt>Páginas lidas</dt><dd>{cov.processed_ranges || "—"} de {cov.total_pages ?? "?"}</dd>
              {cov.not_processed_ranges && <><dt>Não lidas</dt><dd>{cov.not_processed_ranges}</dd></>}
              {cov.without_text_ranges && <><dt>Sem texto</dt><dd>{cov.without_text_ranges}</dd></>}</dl>
          )}
        </div>
        <div className="card">
          <h3>Parâmetros</h3>
          <p><strong>{a.totals.parameters}</strong> encontrados em <strong>{a.totals.experiments}</strong> experimento(s)</p>
          <p><Badge tone="ok">{a.totals.reviewed} <Term k="conferido">conferidos</Term></Badge> <Badge tone="warn">{a.totals.pending} <Term k="nao_revisado">pendentes</Term></Badge> <Badge tone="bad">{a.totals.gaps} <Term k="lacuna">lacunas</Term></Badge></p>
          <p className="detail">A origem verificada <strong>não</strong> significa números conferidos.</p>
        </div>
        <div className="card">
          <h3><Term k="enriquecimento">Fontes NASA relacionadas</Term></h3>
          {a.sources.length === 0 ? <p className="detail">Ainda não consultadas.</p> : <ul>{a.sources.map((s) => {
            const l = MATCH_LABEL[s.state] ?? { text: s.state, tone: "muted" as const };
            return <li key={s.source}><strong>{s.source}</strong> <Badge tone={l.tone}>{l.text}</Badge>{s.record_id && <> <small className="muted">{s.record_id}</small></>}</li>;
          })}</ul>}
          {a.divergences.length > 0 && <p className="detail">⚠ {a.divergences.length} divergência(s) de metadados (ex.: {a.divergences[0].label_pt}).</p>}
          <p className="detail">Não validam os números do artigo.</p>
        </div>
      </div>
      {!compact && (
        <>
          <h2>Experimentos e prontidão para simulação</h2>
          {a.experiments.length === 0 ? <p className="muted">Nenhum experimento identificado.</p> : (
            <table><thead><tr><th>Experimento</th><th>Parâmetros</th><th><Term k="fds">Prontidão FDS</Term></th><th></th></tr></thead><tbody>
              {a.experiments.map((e) => {
                const l = COMPAT_LABEL[e.fds.status ?? ""] ?? { text: e.fds.label_pt, tone: "info" as const };
                return <tr key={e.experiment_id}>
                  <td><strong>{e.label}</strong><div className="detail">{e.phenomena.join(", ") || "fenômeno não classificado"}</div></td>
                  <td>{e.parameters} ({e.reviewed} conferidos · {e.pending} pendentes · {e.gaps} lacunas)</td>
                  <td><Badge tone={l.tone}>{l.text}</Badge>{e.fds.reasons_pt.slice(0, 2).map((r) => <div className="detail" key={r}>{r}</div>)}</td>
                  <td><Link className="btn" to={`/experimentos/${e.experiment_id}`}>Revisar</Link></td></tr>;
              })}
            </tbody></table>
          )}
          <h2>O que ainda não está validado</h2>
          <ul>{a.not_validated_pt.map((t) => <li key={t}>{t}</li>)}</ul>
          <h2>Glossário</h2>
          <dl className="kv glossary">{["procedencia", "sha256", "revisao", "nao_revisado", "cobertura", "enriquecimento", "candidato", "lacuna", "condicao", "observavel", "hipotese"].map((k) => <div key={k} style={{ display: "contents" }}><dt>{k.replace("_", " ")}</dt><dd>{GLOSSARY[k]}</dd></div>)}</dl>
          {a.steps && (
            <details className="tech big"><summary>Processamento e tempos (técnico)</summary>
              {a.metrics?.total_ms != null && <p className="detail">Tempo total do processamento: {formatDuration(a.metrics.total_ms)}</p>}
              <StepList steps={a.steps} />
              {cov.batches && cov.batches.length > 0 && (
                <table><thead><tr><th>Lote</th><th>Páginas</th><th>Caracteres</th><th>Tempo</th><th>Aceitos</th><th>Descartados</th><th>Tokens</th></tr></thead><tbody>
                  {cov.batches.map((b) => <tr key={b.batch}><td>{b.batch}</td><td>{b.pages}</td><td>{b.chars}</td><td>{formatDuration(b.duration_ms)}{b.error ? ` · ERRO ${b.error}` : ""}</td><td>{b.accepted}</td><td>{b.rejected}</td><td>{b.usage?.total_tokens ?? "—"}</td></tr>)}
                </tbody></table>
              )}
            </details>
          )}
        </>
      )}
    </>
  );
}

/** Resumo consolidado de um documento. */
export default function AnalysisPage() {
  const { id = "" } = useParams();
  const a = useLoad(() => api.analysis(id), [id]);
  return (
    <Async state={a}>{(data) => (
      <>
        <div className="crumbs"><Link to="/">Experimentos NASA</Link> › Resumo da análise</div>
        <h1>{data.document.title}</h1>
        <p className="muted">Documento {data.document.document_id} · {data.document.pages ?? "?"} páginas · {data.document.origin === "CURATED" ? "dataset curado" : "importado"}</p>
        <AnalysisSummary a={data} />
        <div className="row">
          <Link className="btn" to={`/documentos/${id}/enriquecimento`}>Ver fontes NASA em detalhe</Link>
          {data.experiments[0] && <Link className="btn primary" to={`/experimentos/${data.experiments[0].experiment_id}`}>Revisar parâmetros</Link>}
        </div>
      </>
    )}</Async>
  );
}
