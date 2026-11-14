import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, api, type ImportRecord } from "../api";
import { ErrorBox, Provenance, Steps } from "../components";

/** S02 — Importação e processamento. O estado de cada etapa vem do backend (nada é animado). */
export default function Import() {
  const [rec, setRec] = useState<ImportRecord | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  async function send(file: File) {
    setBusy(true); setError(null); setRec(null);
    try { setRec(await api.upload(file)); } catch (e) { setError(e as ApiError); } finally { setBusy(false); }
  }

  useEffect(() => {
    if (!rec || rec.status !== "PROCESSING") return;
    const t = setInterval(async () => { try { setRec(await api.importRecord(rec.import_id)); } catch { /* tenta de novo */ } }, 1200);
    return () => clearInterval(t);
  }, [rec]);

  const doc = rec?.document;
  return (
    <>
      <h1>Importar artigo</h1>
      <p className="muted">Envie um artigo da NASA em PDF. O arquivo é tratado como conteúdo não confiável: só o texto é lido. A consulta às fontes NASA e a extração por IA são opcionais; se falharem, o artigo continua disponível.</p>
      <div className="drop">
        <input ref={input} type="file" accept="application/pdf" hidden onChange={(e) => e.target.files?.[0] && send(e.target.files[0])} />
        <button className="primary" disabled={busy} onClick={() => input.current?.click()}>{busy ? "Enviando…" : "Escolher PDF"}</button>
        <p className="muted"><small>Máximo 120 MB. Somente PDF com camada de texto (sem OCR nesta versão).</small></p>
      </div>
      {error && <ErrorBox error={error} />}
      {rec && doc && (
        <>
          <h2>Processamento</h2>
          <div className="card">
            <dl className="kv">
              <dt>Arquivo</dt><dd>{rec.filename}</dd>
              <dt>SHA-256</dt><dd><code>{rec.sha256}</code></dd>
              <dt>Título identificado</dt><dd>{doc.title ?? <span className="muted">não identificado</span>}</dd>
              <dt>Páginas</dt><dd>{doc.page_count}</dd>
              <dt>Procedência NASA</dt><dd>{rec.nasa_provenance ? <Provenance p={rec.nasa_provenance} /> : <span className="muted">aguardando verificação…</span>}</dd>
            </dl>
            <Steps steps={rec.steps.map((s) => ({ key: s.key, label: s.label_pt, state: s.state, detail: s.detail_pt }))} />
            {rec.warnings_pt.map((w) => <div className="box warn" key={w}>{w}</div>)}
          </div>
          {rec.nasa_provenance && rec.nasa_provenance.state !== "VERIFIED" && (
            <div className="box warn">A procedência NASA <strong>não foi verificada</strong>. O documento permanece pendente e não é tratado como publicação NASA validada. {rec.nasa_provenance.reasons_pt.join(" ")}</div>
          )}
          {rec.status !== "PROCESSING" && (
            <div className="row">
              <Link className="btn primary" to={`/documentos/${doc.document_id}/enriquecimento`}>Ver fontes NASA</Link>
              {rec.experiments.map((e) => <Link className="btn" key={e.experiment_id} to={`/experimentos/${e.experiment_id}`}>Revisar “{e.label}”</Link>)}
              <Link className="btn" to="/">Biblioteca</Link>
            </div>
          )}
          {rec.status !== "PROCESSING" && rec.experiments.length === 0 && <p className="muted">Nenhum experimento foi extraído (IA desligada, sem camada de texto ou sem citações verificáveis). Nada foi inventado.</p>}
        </>
      )}
    </>
  );
}
