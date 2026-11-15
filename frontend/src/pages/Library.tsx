import { Link } from "react-router-dom";
import { api } from "../api";
import { Async, Badge, DataKind, Provenance, Term, useLoad } from "../components";
import { fmtBytes } from "../lib";

/** S01 — Experimentos NASA. Lista documentos e experimentos reais do catálogo; não presume que exista um "M1". */
export default function Library() {
  const docs = useLoad(api.documents, []);
  return (
    <>
      <div className="row">
        <div className="grow">
          <h1>Experimentos NASA</h1>
          <p className="muted">Artigos NASA e os experimentos descritos neles. O caso de referência do protótipo é o relatório BASS-II; qualquer outro artigo importado aparece aqui da mesma forma. A simulação de demonstração do FDS é independente e fica em “Demonstração FDS”.</p>
        </div>
        <Link className="btn primary" to="/importar">Importar artigo</Link>
      </div>
      <Async state={docs}>{(list) => list.length === 0 ? <p className="muted">Nenhum documento ainda.</p> : (
        <div className="grid">{list.map((d) => (
          <div className="card" key={d.document_id}>
            <div className="row"><Badge tone="info">{d.origin === "CURATED" ? "Dataset curado" : "Importado"}</Badge><Provenance p={d.nasa_provenance} /></div>
            <h3>{d.title}</h3>
            <small className="muted">{fmtBytes(d.size_bytes)}</small>
            <h3>Experimentos ({d.experiments.length})</h3>
            {d.experiments.length === 0 && <p className="muted">Nenhum experimento extraído. O artigo continua disponível para análise e enriquecimento.</p>}
            {d.experiments.map((e) => (
              <div className="row" key={e.experiment_id}>
                <Link to={`/documentos/${d.document_id}/analise`}><strong>{e.label}</strong></Link>
                <DataKind kind={e.review.reviewed === e.review.total && e.review.total > 0 ? "REAL" : "REVISAO"} />
                <small className="muted">{e.review.reviewed}/{e.review.total} <Term k="conferido">conferidos</Term> · {e.review.gaps} pendências acionáveis</small>
                <small>Modelo: {e.model_state_pt ?? "consultar prontidão no resumo"}.</small>
                <Link className="btn" to={`/documentos/${d.document_id}/analise`}>{e.review.gaps ? "Resolver pendências":"Ver próxima ação"}</Link>
              </div>
            ))}
            <div className="row" style={{ marginTop: 10 }}>
              <Link className="btn primary" to={`/documentos/${d.document_id}/analise`}>Resumo da análise</Link>
              <Link className="btn" to={`/documentos/${d.document_id}/enriquecimento`}>Fontes NASA</Link>
            </div>
          </div>
        ))}</div>
      )}</Async>
    </>
  );
}
