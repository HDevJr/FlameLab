import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, api, type Analysis, type ImportRecord } from "../api";
import { ErrorBox, Provenance, StepList, Term } from "../components";
import { formatDuration } from "../lib";
import { AnalysisSummary } from "./Analysis";

/** S02 — Importação. O estado de cada etapa e o tempo vêm do backend (nada é animado nem estimado). */
export default function Import() {
  const [rec, setRec] = useState<ImportRecord | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  async function send(file: File) {
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
      <div className="drop">
        <input ref={input} type="file" accept="application/pdf" hidden onChange={(e) => e.target.files?.[0] && send(e.target.files[0])} />
        <button className="primary" disabled={busy} onClick={() => input.current?.click()}>{busy ? "Enviando…" : "Escolher PDF"}</button>
        <p className="muted"><small>Máximo 120 MB. Somente PDF com camada de texto (sem OCR nesta versão).</small></p>
      </div>
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
            <StepList steps={rec.steps} />
            {rec.warnings_pt.map((w) => <div className="box warn" key={w}>{w}</div>)}
          </div>
          {done && analysis && (
            <>
              <h2>O que o FlameLab encontrou</h2>
              <AnalysisSummary a={analysis} compact />
              <div className="row">
                <Link className="btn primary" to={`/documentos/${doc.document_id}/analise`}>Abrir resumo completo</Link>
                {analysis.experiments[0] && <Link className="btn" to={`/experimentos/${analysis.experiments[0].experiment_id}`}>Revisar parâmetros</Link>}
                <Link className="btn" to="/">Experimentos NASA</Link>
              </div>
            </>
          )}
        </>
      )}
    </>
  );
}
