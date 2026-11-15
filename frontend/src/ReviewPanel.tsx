import { useEffect, useMemo, useState } from "react";
import { ApiError, api, documentFileUrl, type Enrichment, type Experiment, type FieldComparison, type Parameter, type RecordContext, type ReviewEvent, type ReviewPreview, type SemanticFlag } from "./api";
import { Badge, Term } from "./components";
import { FIELD_OK, FIELD_STATUS, LABEL_SOURCE, STATUS_LABEL, failedFields, highlightSegments, reviewErrorMessage, valueText } from "./lib";

const NAME_KEY = "flamelab.reviewer";
const readName = () => { try { return localStorage.getItem(NAME_KEY) ?? ""; } catch { return ""; } };

function Highlight({ text, terms }: { text: string; terms: string[] }) {
  return <>{highlightSegments(text, terms).map((s, i) => (s.hit ? <mark key={i}>{s.text}</mark> : <span key={i}>{s.text}</span>))}</>;
}

const show = (v: string | number | null | undefined) => (v === null || v === undefined || v === "" ? "—" : String(v));

/** Tabela de correspondência por campo: extraído × informado × resultado (mesma lógica do servidor). */
export function ComparisonRows({ rows }: { rows: FieldComparison[] }) {
  return (
    <table className="cmp"><thead><tr><th>Campo</th><th>Extraído pela IA</th><th>Informado</th><th>Correspondência</th></tr></thead><tbody>
      {rows.map((c) => {
        const s = FIELD_STATUS[c.status] ?? { text: c.status, tone: "muted" as const };
        return (
          <tr key={c.field} className={FIELD_OK.has(c.status) ? "" : "failed"}>
            <td><strong>{c.label_pt}</strong></td><td>{show(c.expected)}</td><td>{show(c.received)}</td>
            <td><Badge tone={s.tone}>{s.text}</Badge>{c.detail_pt && <div className="detail">{c.detail_pt}</div>}</td>
          </tr>
        );
      })}
    </tbody></table>
  );
}

function FlagList({ flags }: { flags: SemanticFlag[] }) {
  return <>{flags.map((f) => (
    <div key={f.code} className={`box ${f.severity === "BLOCKING" ? "bad" : "info"}`}>
      <strong>{f.severity === "BLOCKING" ? "⚠ Ambiguidade científica: " : "ℹ "}{f.title_pt}</strong>
      <div className="detail" style={{ color: "inherit" }}>{f.detail_pt}</div>
    </div>
  ))}</>;
}

function EventLine({ e }: { e: ReviewEvent }) {
  const verb = e.action === "CONFIRM" ? "conferência" : e.action === "CORRECT" ? "correção" : e.action === "DOUBT" ? "dúvida" : "divergência";
  const tone = e.outcome === "APPROVED" ? "ok" : e.outcome === "REFUSED" ? "bad" : "warn";
  const word = { APPROVED: "aprovada", REFUSED: "recusada", RECORDED: "registrada", CORRECTED: "corrigida" }[e.outcome];
  const failed = (e.comparisons ?? []).filter((c) => !FIELD_OK.has(c.status));
  return (
    <li>
      <small className="muted">{e.at}</small> · <strong>{e.reviewer || "—"}</strong> · {verb} → <Badge tone={tone}>{word}</Badge>
      {e.prefilled_unchanged && <small className="muted"> · campos mantidos como extraídos</small>}
      {e.notes && <div className="detail">{e.notes}</div>}
      {e.message && <div className="detail">{e.message}</div>}
      {failed.map((c) => <div className="detail" key={c.field}>• {c.label_pt}: esperado {show(c.expected)}, informado {show(c.received)} ({FIELD_STATUS[c.status]?.text ?? c.status})</div>)}
      {e.outcome === "CORRECTED" && <div className="detail">antes: {JSON.stringify(e.before)} → depois: {JSON.stringify(e.after)}</div>}
    </li>
  );
}

type Props = { exp: Experiment; param: Parameter; onChanged: () => void; onClose: () => void };

/** Revisão científica assistida: a IA leu e organizou as evidências; a pessoa confere o SIGNIFICADO. */
export default function ReviewPanel({ exp, param, onChanged, onClose }: Props) {
  const initValue = valueText(param.original?.value);
  const initUnit = param.unit_info?.display ?? (param.unit_info?.supported === false ? param.original?.unit ?? "" : "");
  const initPage = param.evidence[0]?.page_pdf ? String(param.evidence[0].page_pdf) : "";
  const [reviewer, setReviewer] = useState(readName);
  const [value, setValue] = useState(initValue);
  const [unit, setUnit] = useState(initUnit);
  const [page, setPage] = useState(initPage);
  const [notes, setNotes] = useState("");
  const [checked, setChecked] = useState(false);
  const [correcting, setCorrecting] = useState(false);
  const [cLabel, setCLabel] = useState(param.label_pt);
  const [cValue, setCValue] = useState(initValue);
  const [cUnit, setCUnit] = useState(initUnit);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ApiError | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [preview, setPreview] = useState<ReviewPreview | null>(null);
  const [ctx, setCtx] = useState<RecordContext | null>(null);
  const [enr, setEnr] = useState<Enrichment | null>(null);
  const pending = param.status === "EXTRAIDO_NAO_REVISADO";
  const label = STATUS_LABEL[param.status] ?? { text: param.status, tone: "muted" as const };
  const flags = param.semantic_flags ?? [];
  const blockers = flags.filter((f) => f.severity === "BLOCKING");
  const numeric = typeof param.original?.value === "number";
  const prefilledUnchanged = value === initValue && unit === initUnit && page === initPage;

  useEffect(() => { if (exp.document_id) api.enrichment(exp.document_id).then(setEnr).catch(() => setEnr(null)); }, [exp.document_id]);
  useEffect(() => { api.recordContext(param.record_id, 0).then(setCtx).catch(() => setCtx(null)); }, [param.record_id]);

  // Prévia por campo: a MESMA lógica do servidor (o backend segue sendo a autoridade final).
  useEffect(() => {
    if (!pending) return;
    let alive = true;
    const t = setTimeout(() => {
      api.reviewPreview(param.record_id, { reviewer: reviewer || null, observed_value: value || null, observed_unit: unit || null, observed_page_pdf: page ? Number(page) : null })
        .then((p) => alive && setPreview(p)).catch(() => alive && setPreview(null));
    }, 250);
    return () => { alive = false; clearTimeout(t); };
  }, [param.record_id, pending, reviewer, value, unit, page]);

  const terms = useMemo(() => [initValue, param.unit_info?.display ?? "", ...flags.flatMap((f) => f.terms)], [initValue, param.unit_info, flags]);
  const rows: FieldComparison[] = preview?.comparisons ?? [];

  const why: string[] = [];
  if (!reviewer.trim()) why.push("informe seu nome");
  if (!checked) why.push("marque que verificou a evidência no PDF");
  if (preview && !preview.fields_accepted) why.push(`corrija ${failedFields(preview.comparisons).map((f) => ({ value: "o valor", unit: "a unidade", page: "a página" }[f] ?? f)).join(", ")}`);
  if (preview?.blocking_flags.length) why.push("há ambiguidade científica: corrija a extração ou mantenha pendente");
  if (preview?.reviewer_issue) why.push(reviewErrorMessage(preview.reviewer_issue, preview.reviewer_issue));

  async function send(action: "CONFIRM" | "CORRECT" | "DOUBT" | "DIVERGENCE") {
    setBusy(true); setErr(null); setOk(null);
    try { localStorage.setItem(NAME_KEY, reviewer); } catch { /* sem armazenamento */ }
    try {
      const r = await api.review(param.record_id, {
        action, reviewer, observed_value: value || null, observed_unit: unit || null, observed_page_pdf: page ? Number(page) : null,
        notes: notes || null, checked_pdf: checked, prefilled_unchanged: prefilledUnchanged,
        ...(action === "CORRECT" ? { corrected_label_pt: cLabel !== param.label_pt ? cLabel : null, corrected_value: cValue !== initValue ? cValue : null, corrected_unit: cUnit !== initUnit ? cUnit : null } : {}),
      });
      setOk(action === "CONFIRM" ? "Conferência registrada: o valor agora está “Conferido na fonte”."
        : action === "CORRECT" ? `Extração corrigida${r.reopened ? " e a conferência anterior foi reaberta" : ""}. A extração original foi preservada; o valor continua pendente de conferência por outra pessoa.`
        : action === "DOUBT" ? "Dúvida registrada. O valor continua pendente." : "Divergência registrada. O valor continua pendente e não foi alterado.");
      if (action === "CORRECT") setCorrecting(false);
      onChanged();
    } catch (e) {
      const a = e as ApiError;
      setErr(new ApiError(a.status, a.code, reviewErrorMessage(a.code, a.message), a.details));
      onChanged();
    } finally { setBusy(false); }
  }

  const matches = enr?.matches.filter((m) => ["MATCH_CONFIRMED", "MATCH_CANDIDATE"].includes(m.state)) ?? [];
  const compl = enr?.records.filter((r) => r.scope === "EXPERIMENT_PARAMETER" && r.field === param.parameter && r.complementary_value != null) ?? [];
  const evidence = param.evidence[0];

  return (
    <aside className="panel" aria-label={`Revisão de ${param.label_pt}`}>
      <div className="row"><div className="grow"><h2 style={{ margin: 0 }}>{param.label_pt}</h2>
        <small className="muted">nome técnico: <code>{param.technical_name ?? param.parameter}</code>{param.label_source ? ` · ${LABEL_SOURCE[param.label_source]}` : ""}</small></div>
        <button onClick={onClose} aria-label="Fechar painel">✕</button></div>

      <h3>1. Extração encontrada</h3>
      <dl className="kv">
        <dt>Valor</dt><dd><strong className="big">{show(param.original?.value)}</strong></dd>
        <dt>Unidade</dt><dd>{param.unit_info?.display ? <><strong>{param.unit_info.display}</strong> <small className="muted">({param.unit_info.dimension_pt})</small></> : param.unit_info && !param.unit_info.supported ? <><strong>{param.original?.unit}</strong> <Badge tone="warn">fora da tabela de unidades</Badge></> : <span className="muted">sem unidade</span>}</dd>
        <dt>Tipo</dt><dd>{param.role === "CONDICAO" ? <Term k="condicao">condição de entrada</Term> : param.role === "OBSERVAVEL" ? <Term k="observavel">resultado observado</Term> : "metadado"}</dd>
        <dt>Estado</dt><dd><Badge tone={label.tone}>{label.text}</Badge></dd>
        <dt>Experimento</dt><dd>{exp.label} <small className="muted">({exp.experiment_id})</small></dd>
        <dt>Extraído por</dt><dd>{param.extraction ? `${param.extraction.by} (${param.extraction.method})` : "—"}</dd>
      </dl>
      {param.original_extraction && <p className="detail">Extração original da IA preservada: “{param.original_extraction.label_pt}”, {show(param.original_extraction.original.value)} {param.original_extraction.original.unit ?? ""}.</p>}

      <h3>2. Evidência no artigo</h3>
      {!evidence ? <p className="muted">Sem evidência registrada: este valor não pode ser aprovado.</p> : (
        <div className="quote">
          <div><strong>{evidence.locator_pt || `p. ${evidence.page_pdf} do PDF`}</strong>{evidence.page_pdf ? <> · página <strong>{evidence.page_pdf}</strong> do PDF</> : null}</div>
          {evidence.quote && <blockquote><Highlight text={evidence.quote} terms={terms} /></blockquote>}
          {ctx?.found && <details className="tech"><summary>Ver contexto da página</summary>
            <p className="context"><span className="muted">{ctx.before ? `…${ctx.before}` : ""}</span> <mark className="q"><Highlight text={ctx.quote ?? ""} terms={terms} /></mark> <span className="muted">{ctx.after ? `${ctx.after}…` : ""}</span></p></details>}
          {ctx && !ctx.found && ctx.reason_pt && <div className="detail">Contexto: {ctx.reason_pt}.</div>}
          {exp.document_id && evidence.page_pdf && <a className="btn" href={documentFileUrl(exp.document_id, evidence.page_pdf)} target="_blank" rel="noreferrer">Abrir o PDF na página {evidence.page_pdf}</a>}
        </div>
      )}
      {param.caveats_pt.map((c) => <div className="detail" key={c}>⚠ {c}</div>)}
      {flags.length > 0 && <FlagList flags={flags} />}
      {!pending && blockers.length > 0 && <div className="box warn">Este valor está conferido, mas há ambiguidade científica sinalizada. Se a interpretação não for sustentada pelo trecho, use “Corrigir extração” (a conferência será reaberta).</div>}
      <h3>Dados complementares NASA</h3>
      {compl.length > 0 ? compl.map((r, i) => <p key={i}>{String(r.complementary_value)} <small className="muted">({r.complementary_source})</small></p>) :
        <p className="detail">Nenhuma fonte NASA consultada fornece valor para este parâmetro. {matches.length > 0 ? "Fontes relacionadas (contexto, não validam o número): " + matches.map((m) => `${m.source} ${m.source_record_id ?? ""}`).join("; ") + "." : enr ? "" : "O enriquecimento ainda não foi executado."} <Term k="enriquecimento">O que é isto?</Term></p>}

      {pending ? (
        <>
          <h3>3. Conferência</h3>
          <p className="detail">Os campos vêm preenchidos com o que a IA extraiu. Confira com o PDF e altere apenas se o artigo mostrar outro valor. A correspondência abaixo usa a mesma lógica do servidor.</p>
          <table className="cmp"><thead><tr><th>Campo</th><th>Extraído pela IA</th><th>Informado por você</th><th>Correspondência</th></tr></thead><tbody>
            {(["value", "unit", "page"] as const).map((f) => {
              const c = rows.find((r) => r.field === f);
              const s = c ? (FIELD_STATUS[c.status] ?? { text: c.status, tone: "muted" as const }) : null;
              const exp0 = f === "value" ? show(initValue) : f === "unit" ? show(param.unit_info?.display ?? param.original?.unit) : show(initPage);
              return (
                <tr key={f} className={c && !FIELD_OK.has(c.status) ? "failed" : ""}>
                  <td><strong>{f === "value" ? "Valor" : f === "unit" ? "Unidade" : "Página"}</strong></td>
                  <td>{exp0}</td>
                  <td>{f === "value" && <input type="text" aria-label="Valor informado" value={value} onChange={(e) => setValue(e.target.value)} />}
                    {f === "unit" && <input type="text" aria-label="Unidade informada" value={unit} onChange={(e) => setUnit(e.target.value)} placeholder={numeric ? "ex.: °C" : "(sem unidade)"} />}
                    {f === "page" && <input type="number" min={1} aria-label="Página informada" value={page} onChange={(e) => setPage(e.target.value)} />}</td>
                  <td>{s ? <><Badge tone={s.tone}>{s.text}</Badge>{c?.detail_pt && <div className="detail">{c.detail_pt}</div>}</> : <span className="muted">…</span>}</td>
                </tr>
              );
            })}
          </tbody></table>
          <div className="form">
            <label>Seu nome <input type="text" value={reviewer} onChange={(e) => setReviewer(e.target.value)} placeholder="Nome Sobrenome" /></label>
            <label className="wide">Observações / motivo <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} /></label>
            <label className="wide row"><input type="checkbox" checked={checked} onChange={(e) => setChecked(e.target.checked)} /> Verifiquei a evidência no PDF original.</label>
          </div>
          {err && <ReviewError err={err} />}
          {ok && <div className="box ok" role="status">{ok}</div>}

          <h3>4. Ação</h3>
          <div className="row">
            <button className="primary" disabled={busy || why.length > 0} onClick={() => send("CONFIRM")}>Confirmar interpretação</button>
            <button disabled={busy || exp.origin === "CURATED"} onClick={() => setCorrecting((v) => !v)} title={exp.origin === "CURATED" ? "Dataset curado: corrigido pela curadoria" : "Corrigir o nome, o valor ou a unidade extraídos"}>Corrigir extração</button>
            <button disabled={busy || !reviewer.trim() || !notes.trim()} onClick={() => send("DOUBT")} title="Mantém o valor pendente e registra sua dúvida">Marcar dúvida</button>
            <button disabled={busy || !reviewer.trim() || !notes.trim() || !value.trim()} onClick={() => send("DIVERGENCE")} title="O PDF mostra outro valor: registra, sem alterar o dado">Registrar divergência</button>
          </div>
          {why.length > 0 && <p className="detail" aria-live="polite">Para confirmar: {why.join("; ")}.</p>}
          {correcting && (
            <div className="card">
              <strong>Corrigir extração</strong>
              <p className="detail">A extração original da IA é preservada. A conferência fica pendente e outra pessoa precisa confirmá-la. Descreva o motivo em “Observações”.</p>
              <div className="form">
                <label className="wide">Nome do parâmetro<input type="text" value={cLabel} onChange={(e) => setCLabel(e.target.value)} /></label>
                <label>Valor<input type="text" value={cValue} onChange={(e) => setCValue(e.target.value)} /></label>
                <label>Unidade<input type="text" value={cUnit} onChange={(e) => setCUnit(e.target.value)} /></label>
              </div>
              <button className="primary" disabled={busy || !reviewer.trim() || !notes.trim()} onClick={() => send("CORRECT")}>Salvar correção</button>
            </div>
          )}
          <p className="detail">Dúvida e divergência exigem observações (divergência também o valor informado) e nunca alteram o dado. A identidade do revisor é declarada por você; este protótipo não autentica pessoas.</p>
        </>
      ) : (
        <>
          <p className="detail">Este valor já está “{label.text}”.</p>
          {param.review && <div className="box ok">Conferido por <strong>{param.review.reviewer}</strong> em {param.review.reviewed_at}. Hash do PDF conferido: <code>{(param.review.checked_document_sha256 ?? "").slice(0, 16)}…</code></div>}
          {exp.origin !== "CURATED" && <button onClick={() => setCorrecting((v) => !v)}>Corrigir extração (reabre a conferência)</button>}
          {correcting && exp.origin !== "CURATED" && (
            <div className="card"><div className="form">
              <label className="wide">Nome do parâmetro<input type="text" value={cLabel} onChange={(e) => setCLabel(e.target.value)} /></label>
              <label>Valor<input type="text" value={cValue} onChange={(e) => setCValue(e.target.value)} /></label>
              <label>Unidade<input type="text" value={cUnit} onChange={(e) => setCUnit(e.target.value)} /></label>
              <label>Seu nome<input type="text" value={reviewer} onChange={(e) => setReviewer(e.target.value)} /></label>
              <label className="wide">Motivo<textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} /></label>
            </div>
              {err && <ReviewError err={err} />}{ok && <div className="box ok" role="status">{ok}</div>}
              <button className="primary" disabled={busy || !reviewer.trim() || !notes.trim()} onClick={() => send("CORRECT")}>Salvar correção</button></div>
          )}
        </>
      )}

      <h3>Trilha de auditoria</h3>
      {(param.events ?? []).length === 0 ? <p className="detail">Nenhum registro de revisão ainda.</p> : <ul className="audit">{param.events!.map((e, i) => <EventLine key={i} e={e} />)}</ul>}
    </aside>
  );
}

/** Mensagem de recusa com o diagnóstico por campo (qual campo falhou e por quê). */
export function ReviewError({ err }: { err: ApiError }) {
  const d = err.details;
  return (
    <div role="alert">
      <div className="box bad"><strong>Não foi possível concluir.</strong> {err.message} <small>({err.code})</small></div>
      {d && d.comparisons?.length > 0 && <><p className="detail">Campos que falharam: <strong>{failedFields(d.comparisons).join(", ") || "nenhum (veja a interpretação)"}</strong></p><ComparisonRows rows={d.comparisons} /></>}
      {d?.semantic_flags && d.semantic_flags.length > 0 && <FlagList flags={d.semantic_flags} />}
    </div>
  );
}
