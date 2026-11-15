import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, api, type Experiment, type Gap, type Parameter } from "../api";
import { Async, Badge, DataKind, ErrorBox, ReadinessPanel, Term, UnitCell, useLoad } from "../components";
import ReviewPanel from "../ReviewPanel";
import GuidedReview from "../GuidedReview";
import { groupGaps } from "../gap_themes";
import { COVERAGE_STATE, groupByRole, isStaleBackend, reviewStateView, valueText } from "../lib";

function ParamTable({ rows, title, hint, selected, onSelect }: { rows: Parameter[]; title: string; hint: string; selected: string | null; onSelect: (id: string) => void }) {
  if (!rows.length) return null;
  return (
    <>
      <h2>{title}</h2><p className="muted">{hint}</p>
      <table className="selectable"><thead><tr><th>Parâmetro</th><th>Valor</th><th>Unidade</th><th>Estado da revisão</th><th>Origem</th><th></th></tr></thead><tbody>
        {rows.map((p) => {
          const s = reviewStateView(p);
          const bad = (p.integrity?.findings ?? []).filter((f) => f.severity === "BLOCKING");
          const amb = (p.semantic_flags ?? []).some((f) => f.severity === "BLOCKING");
          return (
            <tr key={p.record_id} className={selected === p.record_id ? "sel" : ""}>
              <td><strong>{p.label_pt}</strong><div className="detail"><code>{p.technical_name ?? p.parameter}</code></div>
                {p.condition && <div className="detail">condição: {p.condition.text}</div>}</td>
              <td><strong>{valueText(p.original?.value) || "—"}</strong>{p.normalized && <div className="detail">SI: {valueText(Number(p.normalized.value.toPrecision(8)))} {p.normalized.unit}</div>}</td>
              <td><UnitCell p={p} /></td>
              <td><Badge tone={s.tone}>{s.text}</Badge>
                {bad.length > 0 && <div className="detail" title={bad.map((f) => f.title_pt).join("; ")}>⚠ integridade: {bad.map((f) => f.title_pt).join("; ")}</div>}
                {amb && <div className="detail" title="O trecho não sustenta a interpretação do parâmetro">⚠ ambiguidade científica</div>}
                {(p.events?.length ?? 0) > 0 && <div className="detail">{p.events!.length} registro(s) de revisão</div>}</td>
              <td>{p.evidence.map((e, i) => <div key={i}><small>{e.locator_pt || (e.page_pdf ? `PDF p. ${e.page_pdf}` : "—")}</small></div>)}</td>
              <td><button onClick={() => onSelect(p.record_id)} aria-label={`Ver origem e revisar ${p.label_pt}`}>{p.status === "EXTRAIDO_NAO_REVISADO" ? "Ver origem e revisar" : "Ver origem"}</button></td>
            </tr>
          );
        })}
      </tbody></table>
    </>
  );
}

/** Lacuna: estado de cobertura, parâmetros relacionados (mesma grandeza, escopo a confirmar) e decisão humana rastreável. */
function GapRow({ gap, onDecided }: { gap: Gap; onDecided: () => void }) {
  const [open, setOpen] = useState(false);
  const [reviewer, setReviewer] = useState(() => { try { return localStorage.getItem("flamelab.reviewer") ?? ""; } catch { return ""; } });
  const [notes, setNotes] = useState("");
  const [recordId, setRecordId] = useState(gap.related_parameters?.[0]?.record_id ?? "");
  const [err, setErr] = useState<ApiError | null>(null);
  const state = COVERAGE_STATE[gap.coverage_state ?? "ABERTA"];
  async function decide(decision: "COVERED" | "PARTIAL" | "DISTINCT") {
    setErr(null);
    try { await api.gapDecision(gap.gap_id, { decision, reviewer, notes, record_id: recordId || null }); setOpen(false); onDecided(); } catch (e) { setErr(e as ApiError); }
  }
  const rel = gap.related_parameters ?? [];
  return (
    <tr>
      <td><strong>{gap.label_pt}</strong><div className="detail"><code>{gap.parameter}</code></div></td>
      <td>{gap.explanation_pt}{gap.purpose_blocked.length > 0 && <div className="detail">Bloqueia: {gap.purpose_blocked.join(", ")}</div>}
        {rel.map((r) => (
          <div className="box warn" key={r.record_id}><strong>Possível sobreposição com “{r.label_pt}”</strong> ({valueText(r.value)} {r.unit ?? ""}, p. {r.page}).
            <div className="detail" style={{ color: "inherit" }}>{r.explanation_pt}</div></div>
        ))}
        {gap.decision && <div className="detail">Decisão de {gap.decision.reviewer} em {gap.decision.at}: <strong>{{ COVERED: "coberta", PARTIAL: "cobertura parcial", DISTINCT: "conceito distinto" }[gap.decision.decision]}</strong> — {gap.decision.notes}</div>}
        {rel.length > 0 && <button onClick={() => setOpen((v) => !v)}>{gap.decision ? "Alterar decisão" : "Registrar decisão"}</button>}
        {open && (
          <div className="card">
            <div className="form">
              <label>Seu nome<input type="text" value={reviewer} onChange={(e) => setReviewer(e.target.value)} /></label>
              <label>Parâmetro relacionado<select value={recordId} onChange={(e) => setRecordId(e.target.value)}>{rel.map((r) => <option key={r.record_id} value={r.record_id}>{r.label_pt}</option>)}</select></label>
              <label className="wide">Motivo<textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} /></label>
            </div>
            {err && <ErrorBox error={err} />}
            <div className="row">
              <button disabled={!reviewer.trim() || notes.trim().length < 3} onClick={() => decide("PARTIAL")}>Cobre em parte (a lacuna continua aberta)</button>
              <button disabled={!reviewer.trim() || notes.trim().length < 3} onClick={() => decide("COVERED")}>Cobre totalmente</button>
              <button disabled={!reviewer.trim() || notes.trim().length < 3} onClick={() => decide("DISTINCT")}>São conceitos distintos</button>
            </div>
            <p className="detail">Nada é apagado nem fundido: a decisão fica registrada com revisor, data e motivo.</p>
          </div>
        )}
      </td>
      <td><Badge tone={state.tone}>{state.text}</Badge><div className="detail"><small>{gap.origin === "SUGERIDA_POR_IA" ? "sugerida pela IA (não verificada)" : "curadoria"}</small></div></td>
    </tr>
  );
}

/** Lacunas declaradas, por tema: dado procurado e AUSENTE NA FONTE. Nunca preenchido por estimativa. */
function DeclaredGaps({ gaps }: { gaps: Gap[] }) {
  if (!gaps.length) return null;
  return (
    <section className="card" aria-label="Lacunas declaradas" style={{ borderLeft: "4px solid #D97706" }}>
      <h2 style={{ marginTop: 0 }}>Lacunas declaradas <Badge tone="warn">{gaps.length} AUSENTE NA FONTE</Badge></h2>
      <p className="detail">Procuradas no documento e não encontradas. O FlameLab não as estimou.</p>
      {groupGaps(gaps).map(([theme, list]) => (
        <div className="gap-theme" key={theme}><h4>{theme}</h4>
          {list.map((g) => (
            <div className="gap-item" key={g.gap_id}>
              <div><strong>{g.label_pt}</strong><div className="detail">{g.explanation_pt}</div>
                {g.purpose_blocked.length > 0 && <div className="detail">Impede: {g.purpose_blocked.join(", ")}</div>}</div>
              <Badge tone="warn"><span aria-hidden>⚠</span> AUSENTE NA FONTE</Badge>
            </div>
          ))}
        </div>
      ))}
    </section>
  );
}

/** Ressalvas registradas por parâmetro. Ficam visíveis (não em tooltip), como pede o design. */
function SourceCaveats({ params }: { params: Parameter[] }) {
  const rows = params.filter((p) => (p.caveats_pt?.length ?? 0) > 0);
  if (!rows.length) return null;
  return (
    <section className="card caveat-panel" aria-label="Ressalvas da fonte">
      <h2 style={{ marginTop: 0 }}>Ressalvas da fonte</h2>
      {rows.map((p) => <div key={p.record_id}><strong>{p.label_pt}</strong><ul>{p.caveats_pt.map((c, i) => <li key={i}>{c}</li>)}</ul></div>)}
    </section>
  );
}

/** S04 — Revisão dos parâmetros: integridade, revisão, cobertura, compatibilidade e prontidão como dimensões SEPARADAS. */
export default function Review() {
  const { id = "" } = useParams();
  const exp = useLoad<Experiment>(() => api.experiment(id), [id]);
  const compat = useLoad(() => api.compatibility(id), [id]);
  const [selected, setSelected] = useState<string | null>(null);
  const [reviewRequest,setReviewRequest]=useState(0);
  return (
    <Async state={exp}>{(e) => {
      const g = groupByRole(e.parameters);
      const c = compat.data;
      const sel = e.parameters.find((p) => p.record_id === selected) ?? null;
      const full = e.parameters.filter((p) => p.review_scope === "FULL").length;
      const confirmed = e.parameters.filter((p) => p.status === "CONFERIDO_FONTE").length;
      return (
        <>
          <div className="crumbs"><Link to="/">Experimentos NASA</Link> › <Link to={`/documentos/${e.document_id}/analise`}>{e.document_title ?? e.document_id}</Link> › {e.label}</div>
          {isStaleBackend(e.parameters) && <div className="box bad" role="alert"><strong>Servidor desatualizado.</strong> O backend em execução não envia a classificação das unidades nem a integridade dos parâmetros; as colunas abaixo mostram apenas a unidade bruta do registro. Reinicie o backend para carregar a versão atual.</div>}
          <div className="row"><h1 className="grow">{e.label}</h1><DataKind kind={e.review.reviewed === e.review.total && e.review.total > 0 ? "REAL" : "REVISAO"} /></div>
          {e.gaps.length>0 && <GuidedReview experimentId={id} documentId={e.document_id} count={e.gaps.length} openSignal={reviewRequest}/>}
          <Link className="btn" to={`/experimentos/${id}/preparar`}>Preparar modelo com decisões registradas</Link>
          {e.description && <p className="muted">{e.description}</p>}
          <p><strong>{confirmed}</strong> de <strong>{e.review.total}</strong> parâmetros <Term k="conferido">conferidos</Term> por uma pessoa, dos quais <strong>{full}</strong> com a interpretação também confirmada · <strong>{e.review.gaps}</strong> <Term k="lacuna">lacunas</Term>.
            {confirmed > full && " Conferências anteriores comparavam só número, unidade e página; recomenda-se reconfirmar a interpretação."}</p>

          <div className="card">
            <h3 style={{ marginTop: 0 }}>Prontidão — cinco dimensões independentes</h3>
            <p className="detail">Conferir os parâmetros <strong>não</strong> habilita a simulação: cada dimensão é avaliada separadamente e a execução só fica pronta quando todas estão satisfeitas.</p>
            <ReadinessPanel readiness={c?.readiness} experimentId={id} onResolve={e.gaps.length ? ()=>setReviewRequest(n=>n+1):undefined} />
            <div className="row">
              <a className="btn" href="#parametros">Revisar parâmetros</a>
              <Link className="btn" to={`/experimentos/${id}/preparar`}>Entender requisitos do modelo</Link>
              {c?.actions.simulate && <Link className="btn primary" to={`/experimentos/${id}/preparar`}>Preparar execução</Link>}
              <Link className={`btn ${c?.actions.alter ? "" : "disabled"}`} to={`/experimentos/${id}/alterar`}>Alterar parâmetros (hipótese)</Link>
              <Link className="btn" to={`/documentos/${e.document_id}/enriquecimento`}>Consultar fontes NASA</Link>
            </div>
            <p className="detail">Nenhuma simulação genérica é criada no lugar deste experimento. O caso genérico do FDS é uma demonstração técnica independente: <Link to="/demonstracao-fds">Demonstração FDS</Link>.</p>
          </div>

          <div id="parametros" className={sel ? "split" : ""}>
            <div>
              <ParamTable rows={g.conditions} title="Condições experimentais" hint="Entradas do experimento, como descritas na fonte." selected={selected} onSelect={setSelected} />
              <ParamTable rows={g.observed} title="Resultados observados" hint="Medições do experimento. São referência de comparação, nunca entradas da simulação." selected={selected} onSelect={setSelected} />
              <ParamTable rows={g.metadata} title="Metadados" hint="Identificação do material, do equipamento ou do contexto." selected={selected} onSelect={setSelected} />

              <SourceCaveats params={e.parameters} />
              <DeclaredGaps gaps={e.gaps} />

              <details className="tech big"><summary>Reconciliação técnica de lacunas com parâmetros existentes ({e.gaps.filter(g=>(g.related_parameters?.length ?? 0)>0).length})</summary>
              {e.gaps.length === 0 ? <p className="muted">Nenhuma lacuna registrada.</p> : (
                <table><thead><tr><th>Informação</th><th>Situação</th><th>Cobertura</th></tr></thead><tbody>
                  {e.gaps.filter(g=>(g.related_parameters?.length ?? 0)>0).map((gap) => <GapRow key={gap.gap_id} gap={gap} onDecided={exp.reload} />)}
                </tbody></table>
              )}</details>
            </div>
            {sel && <ReviewPanel key={sel.record_id} exp={e} param={sel} onChanged={exp.reload} onClose={() => setSelected(null)} />}
          </div>
        </>
      );
    }}</Async>
  );
}
