import { useEffect, useMemo, useState } from "react";
import { ApiError, api, documentFileUrl, type Enrichment, type Experiment, type FieldComparison, type IntegrityFinding, type Parameter, type RecordContext, type ReviewEvent, type ReviewPreview, type SemanticFlag } from "./api";
import { Badge, Term, UnitCell } from "./components";
import { FIELD_OK, FIELD_STATUS, LABEL_SOURCE, failedFields, highlightSegments, reviewErrorMessage, reviewStateView, unitView, valueText } from "./lib";

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

function FindingList({ findings }: { findings: IntegrityFinding[] }) {
  return <>{findings.map((f) => (
    <div key={f.code} className={`box ${f.severity === "BLOCKING" ? "bad" : "warn"}`}>
      <strong>{f.severity === "BLOCKING" ? "⚠ Integridade: " : "ℹ "}{f.title_pt}</strong>
      <div className="detail" style={{ color: "inherit" }}>{f.detail_pt}</div>
    </div>
  ))}</>;
}

function EventLine({ e }: { e: ReviewEvent }) {
  const verb = { CONFIRM: "conferência", CORRECT: "correção", REOPEN: "reabertura", DOUBT: "dúvida", DIVERGENCE: "divergência" }[e.action];
  const tone = e.outcome === "APPROVED" ? "ok" : e.outcome === "REFUSED" ? "bad" : "warn";
  const word = { APPROVED: "aprovada", REFUSED: "recusada", RECORDED: "registrada", CORRECTED: "corrigida", REOPENED: "reaberta" }[e.outcome];
  const failed = (e.comparisons ?? []).filter((c) => !FIELD_OK.has(c.status));
  return (
    <li>
      <small className="muted">{e.at}</small> · <strong>{e.reviewer || "—"}</strong> · {verb} → <Badge tone={tone}>{word}</Badge>
      {e.outcome === "APPROVED" && <div className="detail">submetido: valor <strong>{show(e.observed_value)}</strong>, unidade <strong>{show(e.observed_unit)}</strong>, página {show(e.observed_page_pdf)}</div>}
      {e.prefilled_unchanged && <small className="muted"> · campos mantidos como extraídos</small>}
      {e.notes && <div className="detail">{e.notes}</div>}
      {e.message && <div className="detail">{e.message}</div>}
      {failed.map((c) => <div className="detail" key={c.field}>• {c.label_pt}: esperado {show(c.expected)}, informado {show(c.received)} ({FIELD_STATUS[c.status]?.text ?? c.status})</div>)}
      {e.outcome === "CORRECTED" && <div className="detail">antes: {JSON.stringify(e.before)} → depois: {JSON.stringify(e.after)}</div>}
    </li>
  );
}

const UNIT_SOURCE_TEXT: Record<string, string> = {
  QUOTE: "a unidade aparece ao lado do valor no trecho", SYMBOL_UNREADABLE: "a camada de texto traz um símbolo ilegível no lugar da unidade",
  NOT_FOUND: "a unidade NÃO aparece no trecho (pode ter sido inferida)", NOT_CHECKED: "tabela curada: a unidade vem do cabeçalho da coluna",
};

type Props = { exp: Experiment; param: Parameter; onChanged: () => void; onClose: () => void };

/** Revisão científica assistida: a IA leu e organizou as evidências; a pessoa confere o SIGNIFICADO. */
export default function ReviewPanel({ exp, param, onChanged, onClose }: Props) {
  const view = unitView(param);
  const initValue = valueText(param.original?.value);
  const initUnit = param.unit_info?.display ?? (view.kind === "UNKNOWN" || view.kind === "UNSUPPORTED" ? param.original?.unit ?? "" : "");
  const initPage = param.evidence[0]?.page_pdf ? String(param.evidence[0].page_pdf) : "";
  const [reviewer, setReviewer] = useState(readName);
  const [value, setValue] = useState(initValue);
  const [unit, setUnit] = useState(initUnit);
  const [page, setPage] = useState(initPage);
  const [notes, setNotes] = useState("");
  const [checked, setChecked] = useState(false);
  const [interpretation, setInterpretation] = useState(false);
  const [unitVerified, setUnitVerified] = useState(false);
  const [correcting, setCorrecting] = useState(false);
  const [cLabel, setCLabel] = useState(param.label_pt);
  const [cValue, setCValue] = useState(initValue);
  const [cUnit, setCUnit] = useState(initUnit);
  const [cCondText, setCCondText] = useState("");
  const [cCondValue, setCCondValue] = useState("");
  const [cCondUnit, setCCondUnit] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ApiError | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [preview, setPreview] = useState<ReviewPreview | null>(null);
  const [ctx, setCtx] = useState<RecordContext | null>(null);
  const [enr, setEnr] = useState<Enrichment | null>(null);
  const pending = param.status === "EXTRAIDO_NAO_REVISADO";
  const state = reviewStateView(param);
  const flags = param.semantic_flags ?? [];
  const findings = param.integrity?.findings ?? [];
  const blockers = flags.filter((f) => f.severity === "BLOCKING");
  const unreadable = findings.some((f) => f.code === "UNIT_SYMBOL_UNREADABLE");
  const numeric = typeof param.original?.value === "number";
  const prefilledUnchanged = value === initValue && unit === initUnit && page === initPage;
  const curated = exp.origin === "CURATED";

  useEffect(() => { if (exp.document_id) api.enrichment(exp.document_id).then(setEnr).catch(() => setEnr(null)); }, [exp.document_id]);
  useEffect(() => { api.recordContext(param.record_id, 0).then(setCtx).catch(() => setCtx(null)); }, [param.record_id]);

  // Prévia por campo: a MESMA lógica do servidor (o backend segue sendo a autoridade final).
  useEffect(() => {
    if (!pending) return;
    let alive = true;
    const t = setTimeout(() => {
      api.reviewPreview(param.record_id, { reviewer: reviewer || null, observed_value: value || null, observed_unit: unit || null, observed_page_pdf: page ? Number(page) : null, unit_verified_in_pdf: unitVerified })
        .then((p) => alive && setPreview(p)).catch(() => alive && setPreview(null));
    }, 250);
    return () => { alive = false; clearTimeout(t); };
  }, [param.record_id, pending, reviewer, value, unit, page, unitVerified]);

  const terms = useMemo(() => [initValue, param.unit_info?.display ?? "", ...flags.flatMap((f) => f.terms), ...findings.flatMap((f) => f.terms)], [initValue, param.unit_info, flags, findings]);
  const rows: FieldComparison[] = preview?.comparisons ?? [];
  const pdfValue = param.integrity?.pdf_value;
  const candidates = param.integrity?.condition_candidates ?? [];

  const why: string[] = [];
  if (!reviewer.trim()) why.push("informe seu nome");
  if (!checked) why.push("marque que verificou a evidência no PDF");
  if (!interpretation) why.push("confirme a interpretação (o trecho sustenta o significado do parâmetro)");
  if (preview && !preview.fields_accepted) why.push(`corrija ${failedFields(preview.comparisons).map((f) => ({ value: "o valor", unit: "a unidade", page: "a página" }[f] ?? f)).join(", ")}`);
  if (preview?.blocking_integrity?.length) why.push(`há inconsistência de integridade (${preview.blocking_integrity.map((f) => f.title_pt).join("; ")})`);
  if (preview?.blocking_flags.length) why.push("há ambiguidade científica: corrija a extração ou mantenha pendente");
  if (preview?.reviewer_issue) why.push(reviewErrorMessage(preview.reviewer_issue, preview.reviewer_issue));

  async function send(action: "CONFIRM" | "CORRECT" | "REOPEN" | "DOUBT" | "DIVERGENCE") {
    setBusy(true); setErr(null); setOk(null);
    try { localStorage.setItem(NAME_KEY, reviewer); } catch { /* sem armazenamento */ }
    try {
      const r = await api.review(param.record_id, {
        action, reviewer, observed_value: value || null, observed_unit: unit || null, observed_page_pdf: page ? Number(page) : null,
        notes: notes || null, checked_pdf: checked, prefilled_unchanged: prefilledUnchanged, interpretation_confirmed: interpretation, unit_verified_in_pdf: unitVerified,
        ...(action === "CORRECT" ? {
          corrected_label_pt: cLabel !== param.label_pt ? cLabel : null, corrected_value: cValue !== initValue ? cValue : null, corrected_unit: cUnit !== initUnit ? cUnit : null,
          corrected_condition_text: cCondText || null, corrected_condition_value: cCondValue || null, corrected_condition_unit: cCondUnit || null } : {}),
      });
      setOk(action === "CONFIRM" ? "Conferência registrada: número, unidade e interpretação confirmados."
        : action === "CORRECT" ? `Extração corrigida${r.reopened ? " e a conferência anterior foi reaberta" : ""}. A extração original foi preservada; o valor continua pendente de conferência por outra pessoa.`
        : action === "REOPEN" ? "Conferência reaberta: o valor voltou a ficar pendente e o histórico foi preservado."
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
  const comps = param.review?.components;

  return (
    <aside className="panel" aria-label={`Revisão de ${param.label_pt}`}>
      <div className="row"><div className="grow"><h2 style={{ margin: 0 }}>{param.label_pt}</h2>
        <small className="muted">nome técnico: <code>{param.technical_name ?? param.parameter}</code>{param.label_source ? ` · ${LABEL_SOURCE[param.label_source]}` : ""}</small></div>
        <button onClick={onClose} aria-label="Fechar painel">✕</button></div>

      <h3>1. Ficha científica</h3>
      <dl className="ficha" aria-label="Ficha científica do parâmetro">
        <dt>Valor no PDF</dt><dd>{pdfValue?.literal ? <>“<strong>{pdfValue.literal}</strong>” localizado no trecho (p. {evidence?.page_pdf ?? "?"})</> : pdfValue?.found === false ? <Badge tone="bad">não localizado literalmente no trecho</Badge> : <span className="muted">não verificado nesta fonte (tabela curada)</span>}</dd>
        <dt>Interpretado pela IA</dt><dd><strong>{param.label_pt}</strong> = <strong className="big">{show(param.original?.value)}</strong> · {param.role === "CONDICAO" ? <Term k="condicao">condição de entrada</Term> : param.role === "OBSERVAVEL" ? <Term k="observavel">resultado observado</Term> : "metadado"}
          <div className="detail">por {param.extraction ? `${param.extraction.by} (${param.extraction.method})` : "—"}</div></dd>
        <dt>Unidade</dt><dd><UnitCell p={param} />{param.integrity?.unit_source && <div className="detail">{UNIT_SOURCE_TEXT[param.integrity.unit_source]}</div>}
          {view.legacy && <div className="detail">⚠ O servidor não classificou esta unidade (versão antiga): exibida como no registro.</div>}</dd>
        <dt>Grandeza física</dt><dd>{param.unit_info?.dimension_pt ?? <span className="muted">—</span>}
          {param.unit_info?.expected_dimension_pt && <div className="detail">esperada pelo nome do parâmetro: {param.unit_info.expected_dimension_pt}{param.unit_info.dimension_pt && param.unit_info.expected_dimension_pt !== param.unit_info.dimension_pt ? " — ⚠ diverge da unidade" : ""}</div>}</dd>
        <dt>Condição associada</dt><dd>{param.condition ? <><strong>{param.condition.text}</strong> <small className="muted">({param.condition.source === "HUMANO" ? `registrada por ${param.condition.by ?? "pessoa"}` : "proposta pela IA"})</small></>
          : candidates.length > 0 ? <Badge tone="warn">o trecho cita “{candidates[0].text}” — não registrada</Badge> : <span className="muted">nenhuma</span>}</dd>
        <div className="sep" />
        <dt>Confirmação humana</dt><dd>{param.review ? <>por <strong>{param.review.reviewer}</strong> em {param.review.reviewed_at}
          {comps ? <div className="detail">cobriu: número {comps.number ? "✔" : "✖"} · unidade {comps.unit ? "✔" : "n/a"} · interpretação {comps.interpretation ? "✔" : "✖"}{comps.unit_verified_in_pdf ? " · unidade vista no PDF ✔" : ""}</div>
            : <div className="detail">revisão anterior: comparou número, unidade e página; <strong>não confirmou a interpretação</strong>.</div>}</> : <span className="muted">nenhuma</span>}</dd>
        <dt>Estado da revisão</dt><dd><Badge tone={state.tone}>{state.text}</Badge></dd>
        <dt>Experimento</dt><dd>{exp.label} <small className="muted">({exp.experiment_id})</small></dd>
      </dl>
      {param.original_extraction && <p className="detail">Extração original da IA preservada: “{param.original_extraction.label_pt}”, {show(param.original_extraction.original.value)} {param.original_extraction.original.unit ?? ""}.</p>}
      {findings.length > 0 && <FindingList findings={findings} />}

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
      {!pending && (blockers.length > 0 || param.integrity?.status === "INCONSISTENT") && <div className="box warn">Este valor está marcado como conferido, mas há inconsistência ou ambiguidade sinalizada. Use “Reabrir conferência” (mantém o histórico) ou “Corrigir extração”.</div>}
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
            <label className="wide row"><input type="checkbox" checked={interpretation} onChange={(e) => setInterpretation(e.target.checked)} /> Confirmo que o trecho <strong>sustenta o significado</strong> “{param.label_pt}” (conferir o número não basta).</label>
            {unreadable && <label className="wide row"><input type="checkbox" checked={unitVerified} onChange={(e) => setUnitVerified(e.target.checked)} /> Vi a unidade <strong>no PDF</strong> (a camada de texto não a mostra).</label>}
          </div>
          {err && <ReviewError err={err} />}
          {ok && <div className="box ok" role="status">{ok}</div>}

          <h3>4. Ação</h3>
          <div className="row">
            <button className="primary" disabled={busy || why.length > 0} onClick={() => send("CONFIRM")}>Confirmar interpretação</button>
            <button disabled={busy || curated} onClick={() => setCorrecting((v) => !v)} title={curated ? "Dataset curado: corrigido pela curadoria" : "Corrigir o nome, o valor, a unidade ou a condição extraídos"}>Corrigir extração</button>
            <button disabled={busy || !reviewer.trim() || !notes.trim()} onClick={() => send("DOUBT")} title="Mantém o valor pendente e registra sua dúvida">Marcar dúvida</button>
            <button disabled={busy || !reviewer.trim() || !notes.trim() || !value.trim()} onClick={() => send("DIVERGENCE")} title="O PDF mostra outro valor: registra, sem alterar o dado">Registrar divergência</button>
          </div>
          {why.length > 0 && <p className="detail" aria-live="polite">Para confirmar: {why.join("; ")}.</p>}
          {correcting && <CorrectionForm {...{ busy, reviewer, notes, cLabel, setCLabel, cValue, setCValue, cUnit, setCUnit, cCondText, setCCondText, cCondValue, setCCondValue, cCondUnit, setCCondUnit, candidates }} onSave={() => send("CORRECT")} />}
          <p className="detail">Dúvida e divergência exigem observações (divergência também o valor informado) e nunca alteram o dado. A identidade do revisor é declarada por você; este protótipo não autentica pessoas.</p>
        </>
      ) : (
        <>
          <p className="detail">Este valor já está “{state.text}”.</p>
          {!curated && (
            <>
              <div className="form">
                <label>Seu nome<input type="text" value={reviewer} onChange={(e) => setReviewer(e.target.value)} /></label>
                <label className="wide">Motivo<textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} /></label>
              </div>
              {err && <ReviewError err={err} />}{ok && <div className="box ok" role="status">{ok}</div>}
              <div className="row">
                <button disabled={busy || !reviewer.trim() || !notes.trim()} onClick={() => send("REOPEN")} title="Volta o valor para pendente e preserva o histórico">Reabrir conferência</button>
                <button onClick={() => setCorrecting((v) => !v)}>Corrigir extração (reabre a conferência)</button>
              </div>
              {correcting && <CorrectionForm {...{ busy, reviewer, notes, cLabel, setCLabel, cValue, setCValue, cUnit, setCUnit, cCondText, setCCondText, cCondValue, setCCondValue, cCondUnit, setCCondUnit, candidates }} onSave={() => send("CORRECT")} />}
            </>
          )}
        </>
      )}

      <h3>Trilha de auditoria</h3>
      {(param.events ?? []).length === 0 ? <p className="detail">Nenhum registro de revisão ainda.</p> : <ul className="audit">{param.events!.map((e, i) => <EventLine key={i} e={e} />)}</ul>}
    </aside>
  );
}

type CorrectionProps = {
  busy: boolean; reviewer: string; notes: string; cLabel: string; setCLabel: (v: string) => void; cValue: string; setCValue: (v: string) => void; cUnit: string; setCUnit: (v: string) => void;
  cCondText: string; setCCondText: (v: string) => void; cCondValue: string; setCCondValue: (v: string) => void; cCondUnit: string; setCCondUnit: (v: string) => void;
  candidates: { text: string; value: number; unit: string | null }[]; onSave: () => void;
};

function CorrectionForm(p: CorrectionProps) {
  return (
    <div className="card">
      <strong>Corrigir extração</strong>
      <p className="detail">A extração original da IA é preservada. A conferência fica pendente e outra pessoa precisa confirmá-la. Descreva o motivo em “Observações”.</p>
      <div className="form">
        <label className="wide">Nome do parâmetro<input type="text" value={p.cLabel} onChange={(e) => p.setCLabel(e.target.value)} /></label>
        <label>Valor<input type="text" value={p.cValue} onChange={(e) => p.setCValue(e.target.value)} /></label>
        <label>Unidade<input type="text" value={p.cUnit} onChange={(e) => p.setCUnit(e.target.value)} /></label>
        <label className="wide">Condição associada (opcional)<input type="text" value={p.cCondText} onChange={(e) => p.setCCondText(e.target.value)} placeholder={p.candidates[0] ? `ex.: ${p.candidates[0].text}` : "ex.: a 20 °C"} /></label>
        <label>Valor da condição<input type="text" value={p.cCondValue} onChange={(e) => p.setCCondValue(e.target.value)} /></label>
        <label>Unidade da condição<input type="text" value={p.cCondUnit} onChange={(e) => p.setCCondUnit(e.target.value)} /></label>
      </div>
      <button className="primary" disabled={p.busy || !p.reviewer.trim() || !p.notes.trim()} onClick={p.onSave}>Salvar correção</button>
    </div>
  );
}

/** Mensagem de recusa com o diagnóstico por campo (qual campo falhou e por quê). */
export function ReviewError({ err }: { err: ApiError }) {
  const d = err.details;
  return (
    <div role="alert">
      <div className="box bad"><strong>Não foi possível concluir.</strong> {err.message} <small>({err.code})</small></div>
      {d && d.comparisons?.length > 0 && <><p className="detail">Campos que falharam: <strong>{failedFields(d.comparisons).join(", ") || "nenhum (veja a interpretação)"}</strong></p><ComparisonRows rows={d.comparisons} /></>}
      {d?.integrity_findings && d.integrity_findings.length > 0 && <FindingList findings={d.integrity_findings} />}
      {d?.semantic_flags && d.semantic_flags.length > 0 && <FlagList flags={d.semantic_flags} />}
    </div>
  );
}
