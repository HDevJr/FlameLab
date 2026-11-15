import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, api, type Analysis, type ImportRecord } from "../api";
import { Async, Badge, ErrorBox, Provenance, StepList, Term, useLoad } from "../components";
import { fmtBytes, formatDuration } from "../lib";
import { importOutcome } from "../import_outcome";
import { ImportTimeline } from "../ImportTimeline";
import { AnalysisSummary } from "./Analysis";

/** Documentos já importados neste computador, com a situação de cada um. */
function PreviousImports() {
  const docs = useLoad(api.documents, []);
  return (
    <Async state={docs}>{(list) => {
      const imported = list.filter((d) => d.origin === "IMPORTED");
      if (!imported.length) return null;
      return (
        <section aria-label="Importações anteriores">
          <h2>Importações anteriores</h2>
          <div className="grid">{imported.map((d) => (
            <div className="card" key={d.document_id}>
              <h3 style={{ marginTop: 0 }}><Link to={`/documentos/${d.document_id}`}>{d.title || "Título não identificado"}</Link></h3>
              <div className="row"><Provenance p={d.nasa_provenance} /><Badge tone={d.experiments.length ? "info" : "muted"}>{d.experiments.length} experimento(s)</Badge></div>
              <small className="muted">{fmtBytes(d.size_bytes)}</small>
            </div>
          ))}</div>
        </section>
      );
    }}</Async>
  );
}

/** S02 — Importação. O estado de cada etapa e o tempo vêm do backend (nada é animado nem estimado). */
export default function Import() {
  const [rec, setRec] = useState<ImportRecord | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const lastFile = useRef<File | null>(null);

  async function send(file: File) {
    lastFile.current = file;
    setBusy(true); setError(null); setRec(null); setAnalysis(null);
    try { setRec(await api.upload(file)); } catch (e) { setError(e as ApiError); } finally { setBusy(false); }
  }

  useEffect(() => {
    if (!rec || rec.status !== "PROCESSING") return;
    const t = setInterval(async () => { try { setRec(await api.importRecord(rec.import_id)); } catch { /* tenta de novo */ } }, 1000);
    return () => clearInterval(t);
  }, [rec]);

  useEffect(() => {
    if (rec && rec.status !== "PROCESSING") api.analysis(rec.document.document_id).then(setAnalysis).catch(() => setAnalysis(null));
  }, [rec?.status, rec?.document.document_id]); // eslint-disable-line react-hooks/exhaustive-deps

  const doc = rec?.document;
  const done = rec && rec.status !== "PROCESSING";
  return (
    <>
      <h1>Importar artigo</h1>
      <p className="muted">Envie um artigo da NASA em PDF. O arquivo é tratado como conteúdo não confiável: só o texto é lido. A consulta às fontes NASA e a extração por IA são opcionais; se falharem, o artigo continua disponível. Documentos longos podem levar alguns minutos: cada etapa mostra o tempo real decorrido.</p>
      <div className="drop" onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f && !busy) void send(f); }}>
        <input ref={input} type="file" accept="application/pdf" hidden onChange={(e) => e.target.files?.[0] && send(e.target.files[0])} />
        <button className="primary" disabled={busy} onClick={() => input.current?.click()}>{busy ? "Enviando…" : "Escolher PDF"}</button>
        <p className="muted"><small>ou arraste o arquivo para cá</small></p>
        <p className="muted"><small>Máximo 120 MB. Somente PDF com camada de texto (sem OCR nesta versão).</small></p>
      </div>
      {!rec && (
        <>
          <section className="card" aria-label="O que acontece ao importar">
            <h2 style={{ marginTop: 0 }}>O que acontece ao importar</h2>
            <ol className="how">
              <li><strong>Leitura do PDF.</strong> Título, identificadores e páginas com texto. Nada do arquivo é executado.</li>
              <li><strong>Origem NASA.</strong> O FlameLab busca o número do relatório ou o ID no NTRS e só marca “publicação verificada” se o arquivo for idêntico ao distribuído pela NASA.</li>
              <li><strong>Extração por IA</strong> (opcional). Experimentos e parâmetros com citação literal; exige a IA ligada.</li>
              <li><strong>Pendências.</strong> O que a fonte não informa vira lacuna, nunca estimativa, e fica para revisão humana.</li>
            </ol>
            <p className="detail">Reenviar o mesmo PDF reprocessa o documento. Capas escaneadas são lidas com erros de OCR; o título oficial vem do NTRS quando o documento é localizado.</p>
          </section>
          <PreviousImports />
        </>
      )}
      {error && <ErrorBox error={error} />}
      {rec && doc && (
        <>
          <h2>{done ? "Processamento concluído" : "Processando…"}</h2>
          <div className="card">
            <dl className="kv">
              <dt>Arquivo</dt><dd>{rec.filename}</dd>
              <dt>Título identificado</dt><dd>{doc.title ?? <span className="muted">não identificado</span>}</dd>
              <dt><Term k="procedencia">Origem NASA</Term></dt><dd>{rec.nasa_provenance ? <Provenance p={rec.nasa_provenance} /> : <span className="muted">verificando…</span>}</dd>
              <dt>Tempo total</dt><dd>{rec.metrics.total_ms != null ? formatDuration(rec.metrics.total_ms) : <span className="muted">em andamento</span>}</dd>
            </dl>
            {done && (() => {
              const o = importOutcome(rec);
              return (
                <>
                  <ul className="outcome" aria-label="Resultado da importação">
                    {o.rows.map((r) => (
                      <li key={r.key} className={r.tone}>
                        <div className="row"><strong>{r.label}</strong><Badge tone={r.tone}>{r.status}</Badge></div>
                        <div className="detail">{r.detail}</div>
                        {r.action && <div className="next-step"><strong>O que fazer:</strong> {r.action}</div>}
                      </li>
                    ))}
                  </ul>
                  {o.warnings.length > 0 && (
                    <div className="box warn" role="status"><strong>Avisos ({o.warnings.length})</strong>
                      <ul>{o.warnings.map((w) => <li key={w}>{w}</li>)}</ul></div>
                  )}
                </>
              );
            })()}
            <ImportTimeline steps={rec.steps} totalMs={rec.metrics.total_ms} extractProgress={rec.extract_progress} stepProgress={rec.step_progress} />
            <details className="tech big" open={false}><summary>Detalhes técnicos das etapas</summary><StepList steps={rec.steps} /></details>
            {!done && rec.warnings_pt.map((w) => <div className="box warn" key={w}>{w}</div>)}
          </div>
          {done && analysis && (
            <>
              <h2>O que o FlameLab encontrou</h2>
              <AnalysisSummary a={analysis} compact />
              <div className="row">
                {analysis.totals.experiments > 0 ? (
                  <>
                    <Link className="btn primary" to={`/experimentos/${analysis.experiments[0].experiment_id}`}>Revisar parâmetros</Link>
                    <Link className="btn" to={`/documentos/${doc.document_id}/analise`}>Abrir resumo completo</Link>
                  </>
                ) : (
                  <>
                    {lastFile.current && <button className="primary" disabled={busy} onClick={() => lastFile.current && send(lastFile.current)}>Reprocessar este PDF</button>}
                    <Link className="btn" to={`/documentos/${doc.document_id}/analise`}>Abrir resumo do que foi lido</Link>
                  </>
                )}
                <Link className="btn" to="/">Experimentos NASA</Link>
              </div>
            </>
          )}
        </>
      )}
    </>
  );
}
