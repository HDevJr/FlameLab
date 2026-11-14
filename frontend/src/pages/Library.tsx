import { Link } from "react-router-dom";
import { api } from "../api";
import { Async, Badge, DataKind, Provenance, useLoad } from "../components";
import { fmtBytes } from "../lib";

/** S01 — Biblioteca. Lista documentos e experimentos reais do catálogo; não presume que exista um "M1". */
export default function Library() {
  const docs = useLoad(api.documents, []);
  return (
    <>
      <div className="row">
        <div className="grow">
          <h1>Biblioteca</h1>
          <p className="muted">Artigos NASA e os experimentos descritos neles. O caso de referência do protótipo é o relatório BASS-II; qualquer outro artigo importado aparece aqui da mesma forma.</p>
        </div>
        <Link className="btn primary" to="/importar">Importar artigo</Link>
      </div>
      <Async state={docs}>{(list) => list.length === 0 ? <p className="muted">Nenhum documento ainda.</p> : (
        <div className="grid">{list.map((d) => (
          <div className="card" key={d.document_id}>
            <div className="row"><Badge tone="info">{d.origin === "CURATED" ? "Dataset curado" : "Importado"}</Badge><Provenance p={d.nasa_provenance} /></div>
            <h3>{d.title}</h3>
            <small className="muted">{d.document_id} · {fmtBytes(d.size_bytes)}</small>
            <h3>Experimentos ({d.experiments.length})</h3>
            {d.experiments.length === 0 && <p className="muted">Nenhum experimento extraído. O artigo continua disponível para análise e enriquecimento.</p>}
            {d.experiments.map((e) => (
              <div className="row" key={e.experiment_id}>
                <Link to={`/experimentos/${e.experiment_id}`}><strong>{e.label}</strong></Link>
                <DataKind kind={e.review.reviewed === e.review.total && e.review.total > 0 ? "REAL" : "REVISAO"} />
                <small className="muted">{e.review.reviewed}/{e.review.total} conferidos · {e.review.gaps} lacunas</small>
              </div>
            ))}
            <div className="row" style={{ marginTop: 10 }}>
              <Link className="btn" to={`/documentos/${d.document_id}/enriquecimento`}>Fontes NASA</Link>
              {d.experiments[0] && <Link className="btn" to={`/experimentos/${d.experiments[0].experiment_id}`}>Analisar</Link>}
            </div>
          </div>
        ))}</div>
      )}</Async>
    </>
  );
}
