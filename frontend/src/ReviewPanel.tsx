import { useEffect, useState } from "react";
import { ApiError, api, documentFileUrl, type Enrichment, type Experiment, type Parameter } from "./api";
import { Badge, ErrorBox, Term } from "./components";
import { STATUS_LABEL, formatValue, reviewErrorMessage } from "./lib";

const NAME_KEY = "flamelab.reviewer";
const readName = () => { try { return localStorage.getItem(NAME_KEY) ?? ""; } catch { return ""; } };

type Props = { exp: Experiment; param: Parameter; onChanged: () => void; onClose: () => void };

/** Revisão humana de um parâmetro. Mesma política do scripts/review_record.py (aplicada no servidor). */
export default function ReviewPanel({ exp, param, onChanged, onClose }: Props) {
  const [reviewer, setReviewer] = useState(readName);
  const [value, setValue] = useState("");
  const [unit, setUnit] = useState("");
  const [page, setPage] = useState("");
  const [notes, setNotes] = useState("");
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ApiError | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [enr, setEnr] = useState<Enrichment | null>(null);
  const pending = param.status === "EXTRAIDO_NAO_REVISADO";
  const label = STATUS_LABEL[param.status] ?? { text: param.status, tone: "muted" as const };

  useEffect(() => { setValue(""); setUnit(""); setPage(""); setNotes(""); setChecked(false); setErr(null); setOk(null); }, [param.record_id]);
  useEffect(() => { if (exp.document_id) api.enrichment(exp.document_id).then(setEnr).catch(() => setEnr(null)); }, [exp.document_id]);

  async function send(action: "CONFIRM" | "DOUBT" | "DIVERGENCE") {
    setBusy(true); setErr(null); setOk(null);
    try { localStorage.setItem(NAME_KEY, reviewer); } catch { /* sem armazenamento */ }
    try {
      const r = await api.review(param.record_id, {
        action, reviewer, observed_value: value || null, observed_unit: unit || null,
        observed_page_pdf: page ? Number(page) : null, notes: notes || null, checked_pdf: checked,
      });
      setOk(r.outcome === "APPROVED" ? "Conferência registrada: o valor agora está “Conferido na fonte”." :
        action === "DOUBT" ? "Dúvida registrada. O valor continua pendente." : "Divergência registrada. O valor continua pendente e não foi alterado.");
      onChanged();
    } catch (e) {
      const a = e as ApiError;
      setErr(new ApiError(a.status, a.code, reviewErrorMessage(a.code, a.message)));
      onChanged();
    } finally { setBusy(false); }
  }

  const matches = enr?.matches.filter((m) => ["MATCH_CONFIRMED", "MATCH_CANDIDATE"].includes(m.state)) ?? [];
  const compl = enr?.records.filter((r) => r.scope === "EXPERIMENT_PARAMETER" && r.field === param.parameter && r.complementary_value != null) ?? [];

  return (
    <aside className="panel" aria-label={`Revisão de ${param.label_pt}`}>
      <div className="row"><h2 className="grow" style={{ margin: 0 }}>{param.label_pt}</h2><button onClick={onClose} aria-label="Fechar painel">✕</button></div>
      <dl className="kv">
        <dt>Valor extraído</dt><dd><strong>{formatValue(param)}</strong> <Badge tone={label.tone}>{label.text}</Badge></dd>
        <dt>Tipo</dt><dd>{param.role === "CONDICAO" ? <Term k="condicao">condição de entrada</Term> : param.role === "OBSERVAVEL" ? <Term k="observavel">resultado observado</Term> : "metadado"}</dd>
        <dt>Experimento</dt><dd>{exp.label} <small className="muted">({exp.experiment_id})</small></dd>
        <dt>Documento</dt><dd>{exp.document_title ?? exp.document_id}</dd>
        <dt>Extraído por</dt><dd>{param.extraction ? `${param.extraction.by} (${param.extraction.method})` : "—"}</dd>
      </dl>

      <h3>Onde está na fonte</h3>
      {param.evidence.length === 0 ? <p className="muted">Sem evidência registrada: este valor não pode ser aprovado.</p> : param.evidence.map((e, i) => (
        <div className="quote" key={i}>
          <div><strong>{e.locator_pt || (e.page_pdf ? `p. ${e.page_pdf} do PDF` : "—")}</strong>{e.page_pdf ? <> · página <strong>{e.page_pdf}</strong> do PDF</> : null}</div>
          {e.quote && <blockquote>“{e.quote}”</blockquote>}
          {exp.document_id && e.page_pdf && <a className="btn" href={documentFileUrl(exp.document_id, e.page_pdf)} target="_blank" rel="noreferrer">Abrir o PDF na página {e.page_pdf}</a>}
        </div>
      ))}
      {param.caveats_pt.map((c) => <div className="detail" key={c}>⚠ {c}</div>)}

      <h3>Dados complementares NASA</h3>
      {compl.length > 0 ? compl.map((r, i) => <p key={i}>{String(r.complementary_value)} <small className="muted">({r.complementary_source})</small></p>) :
        <p className="detail">Nenhuma fonte NASA consultada fornece valor para este parâmetro. {matches.length > 0 ? "Fontes relacionadas (contexto, não validam o número): " + matches.map((m) => `${m.source} ${m.source_record_id ?? ""}`).join("; ") + "." : enr ? "" : "O enriquecimento ainda não foi executado."} <Term k="enriquecimento">O que é isto?</Term></p>}

      <h3>Trilha de auditoria</h3>
      {param.review && <div className="box ok">Conferido por <strong>{param.review.reviewer}</strong> em {param.review.reviewed_at}. Hash do PDF conferido: <code>{(param.review.checked_document_sha256 ?? "").slice(0, 16)}…</code></div>}
      {(param.events ?? []).length === 0 ? <p className="detail">Nenhum registro de revisão ainda.</p> : (
        <ul className="audit">{param.events!.map((e, i) => (
          <li key={i}><small className="muted">{e.at}</small> · <strong>{e.reviewer || "—"}</strong> · {e.action === "CONFIRM" ? "conferência" : e.action === "DOUBT" ? "dúvida" : "divergência"} →{" "}
            <Badge tone={e.outcome === "APPROVED" ? "ok" : e.outcome === "REFUSED" ? "bad" : "warn"}>{e.outcome === "APPROVED" ? "aprovada" : e.outcome === "REFUSED" ? "recusada" : "registrada"}</Badge>
            {e.notes && <div className="detail">{e.notes}</div>}{e.message && <div className="detail">{e.message}</div>}</li>))}</ul>
      )}

      {pending ? (
        <>
          <h3>Sua conferência</h3>
          <p className="detail">Abra o PDF, localize o valor e <strong>digite o que você leu</strong> (os campos começam vazios de propósito). O servidor só aprova se coincidir com o registro. A identidade do revisor é declarada por você; este protótipo não autentica pessoas.</p>
          <div className="form">
            <label>Seu nome <input type="text" value={reviewer} onChange={(e) => setReviewer(e.target.value)} placeholder="Nome Sobrenome" /></label>
            <label>Valor lido no PDF <input type="text" value={value} onChange={(e) => setValue(e.target.value)} /></label>
            <label>Unidade lida <input type="text" value={unit} onChange={(e) => setUnit(e.target.value)} placeholder="ex.: mm/s (vazio, se não houver)" /></label>
            <label>Página do PDF <input type="number" min={1} value={page} onChange={(e) => setPage(e.target.value)} /></label>
            <label className="wide">Observações / motivo <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} /></label>
            <label className="wide row"><input type="checkbox" checked={checked} onChange={(e) => setChecked(e.target.checked)} /> Conferi o valor no PDF original.</label>
          </div>
          {err && <ErrorBox error={err} />}
          {ok && <div className="box ok" role="status">{ok}</div>}
          <div className="row">
            <button className="primary" disabled={busy || !reviewer.trim()} onClick={() => send("CONFIRM")}>Confirmar conferência</button>
            <button disabled={busy || !reviewer.trim() || !notes.trim()} onClick={() => send("DOUBT")} title="Mantém o valor pendente e registra sua dúvida">Manter pendente (dúvida)</button>
            <button disabled={busy || !reviewer.trim() || !notes.trim() || !value.trim()} onClick={() => send("DIVERGENCE")} title="O PDF mostra outro valor: registra, sem alterar o dado">Registrar divergência</button>
          </div>
          <p className="detail">Dúvida e divergência exigem observações; divergência também exige o valor lido. Nenhuma das duas altera o dado.</p>
        </>
      ) : <p className="detail">Este valor já está “{label.text}”.</p>}
    </aside>
  );
}
