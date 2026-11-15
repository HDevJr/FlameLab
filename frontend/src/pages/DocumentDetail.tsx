import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, documentFileUrl, type Experiment } from "../api";
import { Async, Badge, EmptyState, Provenance, useLoad } from "../components";
import { fmtBytes, valueText } from "../lib";

type Ev = { key: string; experiment: string; parameter: string; value: string; page: number | null; printed: number | null; locator: string; quote: string | null };

/** Evidências de todos os experimentos do documento, agrupadas por página do PDF. Só usa o que o backend registrou. */
export function collectEvidence(exps: Experiment[]): Map<number | null, Ev[]> {
  const by = new Map<number | null, Ev[]>();
  for (const e of exps) for (const p of e.parameters) for (const [i, ev] of p.evidence.entries()) {
    const row: Ev = {
      key: `${p.record_id}-${i}`, experiment: e.label, parameter: p.label_pt, page: ev.page_pdf, printed: ev.page_printed,
      value: `${valueText(p.original?.value) || "—"} ${p.original?.unit ?? ""}`.trim(), locator: ev.locator_pt, quote: ev.quote,
    };
    by.set(ev.page_pdf, [...(by.get(ev.page_pdf) ?? []), row]);
  }
  return new Map([...by.entries()].sort((a, b) => (a[0] ?? 1e9) - (b[0] ?? 1e9)));
}

function Viewer({ id, exps }: { id: string; exps: Experiment[] }) {
  const groups = useMemo(() => collectEvidence(exps), [exps]);
  const [page, setPage] = useState<number | null>(null);
  const pages = [...groups.keys()].filter((p): p is number => p != null);
  const unlinked = groups.get(null) ?? [];
  if (groups.size === 0) return <EmptyState title="Nenhuma evidência registrada para este documento">Evidências aparecem aqui quando há parâmetros extraídos ou curados com localização na fonte.</EmptyState>;
  return (
    <div className="doc-layout">
      <section className="card" aria-label="Evidências por página">
        <h2 style={{ marginTop: 0 }}>Evidências por página ({[...groups.values()].flat().length})</h2>
        {pages.map((pg) => (
          <div key={pg} className={`doc-page ${page === pg ? "sel" : ""}`}>
            <div className="row"><strong>PDF p. {pg}</strong>{groups.get(pg)![0].printed != null && <small className="muted">impressa p. {groups.get(pg)![0].printed}</small>}
              <button className="grow-end" onClick={() => setPage(pg)} aria-pressed={page === pg}>Ver no PDF</button></div>
            <ul>{groups.get(pg)!.map((r) => <li key={r.key}><strong>{r.parameter}</strong> · {r.value} <small className="muted">({r.experiment})</small>
              <div className="detail">{r.locator}</div>{r.quote && <div className="quote">“{r.quote}”</div>}</li>)}</ul>
          </div>
        ))}
        {unlinked.length > 0 && <div className="doc-page"><strong>Referência não vinculada</strong><ul>{unlinked.map((r) => <li key={r.key}>{r.parameter} · {r.value}</li>)}</ul></div>}
      </section>
      <section className="card viewer" aria-label="Documento original">
        <div className="row"><h2 style={{ margin: 0 }} className="grow">Documento original</h2>
          <a className="btn" href={documentFileUrl(id, page ?? undefined)} target="_blank" rel="noreferrer">Abrir em nova aba</a></div>
        {page == null
          ? <p className="muted">Escolha “Ver no PDF” em uma evidência para abrir o documento na página indicada.</p>
          : <><iframe key={page} title={`Documento, página ${page}`} src={documentFileUrl(id, page)} />
              <p className="detail">Alguns navegadores de celular não exibem PDF embutido; use “Abrir em nova aba”.</p></>}
      </section>
    </div>
  );
}

function Evidence({ id, experimentIds }: { id: string; experimentIds: string[] }) {
  const exps = useLoad(() => Promise.all(experimentIds.map((e) => api.experiment(e))), [id, experimentIds.join(",")]);
  return <Async state={exps}>{(list) => <Viewer id={id} exps={list} />}</Async>;
}

/** Detalhe do documento: metadados, procedência, experimentos e evidências com o PDF na página. */
export default function DocumentDetail() {
  const { id = "" } = useParams();
  const doc = useLoad(() => api.document(id), [id]);
  return (
    <Async state={doc}>{(d) => (
      <>
        <div className="crumbs"><Link to="/">Experimentos NASA</Link> › Documento</div>
        <h1>{d.title}</h1>
        <div className="row"><Badge tone="info">{d.origin === "CURATED" ? "Dataset curado" : "Importado"}</Badge><Provenance p={d.nasa_provenance} />
          <Link className="btn" to={`/documentos/${d.document_id}/analise`}>Resumo da análise</Link>
          <Link className="btn" to={`/documentos/${d.document_id}/enriquecimento`}>Fontes NASA</Link></div>
        <dl className="kv card">
          <dt>Identificador</dt><dd><code>{d.document_id}</code></dd>
          <dt>Tamanho</dt><dd>{fmtBytes(d.size_bytes)}</dd>
          <dt>SHA-256</dt><dd><code>{d.sha256 ?? "não disponível"}</code></dd>
          {d.url && <><dt>Fonte</dt><dd><a href={d.url} target="_blank" rel="noreferrer">{d.url}</a></dd></>}
          <dt>Experimentos</dt><dd>{d.experiments.length ? d.experiments.map((e) => <Link key={e.experiment_id} to={`/experimentos/${e.experiment_id}`}>{e.label} </Link>) : "Nenhum extraído"}</dd>
        </dl>
        <Evidence id={d.document_id} experimentIds={d.experiments.map((e) => e.experiment_id)} />
      </>
    )}</Async>
  );
}
