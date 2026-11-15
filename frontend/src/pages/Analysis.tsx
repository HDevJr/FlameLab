import { Link, useParams } from "react-router-dom";
import { api, type Analysis as A } from "../api";
import { Async, Badge, Provenance, StepList, useLoad } from "../components";
import GuidedReview from "../GuidedReview";
import { formatDuration } from "../lib";

/** Conclusions and one next action per experiment; provenance details remain available. */
export function AnalysisSummary({a,compact=false}:{a:A;compact?:boolean}) {
  return <>
    <section className="card headline"><h2>O que o sistema encontrou</h2><p><strong>{a.totals.experiments}</strong> experimentos · <strong>{a.totals.parameters}</strong> parâmetros encontrados · <strong>{a.totals.reviewed}</strong> conferidos por uma pessoa.</p>
      <p>Faltam informações em <strong>{a.totals.gaps}</strong> pendências; {a.totals.pending} parâmetros aguardam conferência.</p>
      <Provenance p={a.provenance}/>
    </section>
    <h2>{compact ? "Próxima ação disponível":"Selecione um experimento para continuar"}</h2>
    <div className="experiment-summaries">{a.experiments.map(e=><article className="card" key={e.experiment_id}>
      <h3>{e.label}</h3><p>{e.reviewed} parâmetros conferidos · {e.gaps} pendências acionáveis.</p>
      <p><Badge tone={e.fds.can_simulate ? "ok":"warn"}>{e.fds.can_simulate ? "Pronto para preparar execução":"Modelo com impedimentos"}</Badge></p>
      {e.gaps>0 ? <GuidedReview experimentId={e.experiment_id} documentId={a.document.document_id} count={e.gaps}/> : <>
        <p>{e.fds.reasons_pt[0] || "Consulte a prontidão do modelo e a revisão dos parâmetros."}</p>
        <Link className="btn primary" to={`/experimentos/${e.experiment_id}${e.fds.can_simulate ? "/preparar":""}`}>{e.fds.can_simulate ? "Preparar execução":"Revisar parâmetros"}</Link>
      </>}
      <p><Link to={`/experimentos/${e.experiment_id}`}>Ver parâmetros e cinco dimensões de prontidão</Link></p>
    </article>)}</div>
    {!a.experiments.length && <p>Nenhum experimento identificado. Consulte o artigo e as fontes disponíveis.</p>}
    <details className="tech big"><summary>Detalhes técnicos da análise e fontes</summary>
      <p>SHA-256: <code>{a.document.sha256 ?? "não disponível"}</code></p><p>{a.coverage.summary_pt}</p>
      <p>Páginas lidas: {a.coverage.processed_ranges || "curadoria / sem leitura automática"}. Não lidas: {a.coverage.not_processed_ranges || "ver cobertura"}.</p>
      {a.sources.map((s,i)=><p key={i}>{s.source}: {s.state_pt} {s.url && <a href={s.url} target="_blank" rel="noreferrer">Consultar fonte</a>}</p>)}
      {a.not_validated_pt.map(t=><p key={t}>{t}</p>)}
      {a.metrics?.total_ms!=null && <p>Tempo de processamento: {formatDuration(a.metrics.total_ms)}</p>}
      {a.steps && <StepList steps={a.steps}/>}
      {a.coverage.batches?.map(b=><p key={b.batch}>Lote {b.batch} · páginas {b.pages} · {formatDuration(b.duration_ms)} · {b.accepted} aceitos · {b.rejected} descartados</p>)}
    </details>
  </>;
}

export default function AnalysisPage(){
  const {id=""}=useParams(); const load=useLoad(()=>api.analysis(id),[id]);
  return <Async state={load}>{a=><><div className="crumbs"><Link to="/">Experimentos NASA</Link> › Resumo da análise</div><h1>{a.document.title}</h1><AnalysisSummary a={a}/><Link className="btn" to={`/documentos/${id}/enriquecimento`}>Consultar fontes NASA relacionadas</Link></>}</Async>;
}
