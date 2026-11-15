import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type Experiment, type Parameter } from "../api";
import { Async, Badge, DataKind, Term, useLoad } from "../components";
import ReviewPanel from "../ReviewPanel";
import { COMPAT_LABEL, STATUS_LABEL, groupByRole, valueText } from "../lib";

function ParamTable({ rows, title, hint, selected, onSelect }: { rows: Parameter[]; title: string; hint: string; selected: string | null; onSelect: (id: string) => void }) {
  if (!rows.length) return null;
  return (
    <>
      <h2>{title}</h2><p className="muted">{hint}</p>
      <table className="selectable"><thead><tr><th>Parâmetro</th><th>Valor</th><th>Unidade</th><th>Estado</th><th>Origem</th><th></th></tr></thead><tbody>
        {rows.map((p) => {
          const s = STATUS_LABEL[p.status] ?? { text: p.status, tone: "muted" as const };
          return (
            <tr key={p.record_id} className={selected === p.record_id ? "sel" : ""}>
              <td><strong>{p.label_pt}</strong><div className="detail"><code>{p.technical_name ?? p.parameter}</code></div></td>
              <td><strong>{valueText(p.original?.value) || "—"}</strong>{p.normalized && <div className="detail">SI: {valueText(Number(p.normalized.value.toPrecision(8)))} {p.normalized.unit}</div>}</td>
              <td>{p.unit_info?.display ?? (p.unit_info && !p.unit_info.supported ? p.original?.unit : <span className="muted">—</span>)}</td>
              <td><Badge tone={s.tone}>{s.text}</Badge>{(p.semantic_flags ?? []).some((f) => f.severity === "BLOCKING") && <div className="detail" title="O trecho não sustenta a interpretação do parâmetro">⚠ ambiguidade científica</div>}{(p.events?.length ?? 0) > 0 && <div className="detail">{p.events!.length} registro(s) de revisão</div>}</td>
              <td>{p.evidence.map((e, i) => <div key={i}><small>{e.locator_pt || (e.page_pdf ? `PDF p. ${e.page_pdf}` : "—")}</small></div>)}</td>
              <td><button onClick={() => onSelect(p.record_id)} aria-label={`Ver origem e revisar ${p.label_pt}`}>{p.status === "EXTRAIDO_NAO_REVISADO" ? "Ver origem e revisar" : "Ver origem"}</button></td>
            </tr>
          );
        })}
      </tbody></table>
    </>
  );
}

/** S04 — Revisão dos parâmetros: condições × resultados observados, origem de cada valor, revisão humana e prontidão FDS. */
export default function Review() {
  const { id = "" } = useParams();
  const exp = useLoad<Experiment>(() => api.experiment(id), [id]);
  const compat = useLoad(() => api.compatibility(id), [id]);
  const [selected, setSelected] = useState<string | null>(null);
  return (
    <Async state={exp}>{(e) => {
      const g = groupByRole(e.parameters);
      const c = compat.data;
      const label = c ? COMPAT_LABEL[c.status] : null;
      const sel = e.parameters.find((p) => p.record_id === selected) ?? null;
      return (
        <>
          <div className="crumbs"><Link to="/">Experimentos NASA</Link> › <Link to={`/documentos/${e.document_id}/analise`}>{e.document_title ?? e.document_id}</Link> › {e.label}</div>
          <div className="row"><h1 className="grow">{e.label}</h1><DataKind kind={e.review.reviewed === e.review.total && e.review.total > 0 ? "REAL" : "REVISAO"} /></div>
          {e.description && <p className="muted">{e.description}</p>}
          <p><strong>{e.review.reviewed}</strong> de <strong>{e.review.total}</strong> parâmetros <Term k="conferido">conferidos</Term> por uma pessoa · <strong>{e.review.gaps}</strong> <Term k="lacuna">lacunas</Term>.
            {e.review.reviewed < e.review.total && " Valores não revisados não devem ser citados como dados da fonte. Use “Ver origem e revisar” em cada linha."}</p>

          <div className="card">
            <div className="row"><h3 style={{ margin: 0 }}>Simulação deste experimento (<Term k="fds">FDS</Term>)</h3>{label && <Badge tone={label.tone}>{label.text}</Badge>}</div>
            {c ? <ul>{c.reasons_pt.map((r) => <li key={r}>{r}</li>)}</ul> : <p className="muted">Avaliando…</p>}
            {c && c.missing.length > 0 && <p className="detail">Faltando para o modelo: {c.missing.join(", ")}</p>}
            <div className="row">
              <button className="primary" disabled={!c?.actions.simulate} title={c?.actions.simulate ? "" : "Indisponível: veja os motivos acima"}>Iniciar simulação deste experimento</button>
              <Link className={`btn ${c?.actions.alter ? "" : "disabled"}`} to={`/experimentos/${id}/alterar`}>Alterar parâmetros (hipótese)</Link>
              <Link className="btn" to={`/documentos/${e.document_id}/enriquecimento`}>Consultar fontes NASA</Link>
            </div>
            <p className="detail">Nenhuma simulação genérica é criada no lugar deste experimento. O caso genérico do FDS é uma demonstração técnica independente: <Link to="/demonstracao-fds">Demonstração FDS</Link>.</p>
          </div>

          <div className={sel ? "split" : ""}>
            <div>
              <ParamTable rows={g.conditions} title="Condições experimentais" hint="Entradas do experimento, como descritas na fonte." selected={selected} onSelect={setSelected} />
              <ParamTable rows={g.observed} title="Resultados observados" hint="Medições do experimento. São referência de comparação, nunca entradas da simulação." selected={selected} onSelect={setSelected} />
              <ParamTable rows={g.metadata} title="Metadados" hint="Identificação do material, do equipamento ou do contexto." selected={selected} onSelect={setSelected} />

              <h2>Campos ausentes ({e.gaps.length})</h2>
              {e.gaps.length === 0 ? <p className="muted">Nenhuma lacuna registrada.</p> : (
                <table><thead><tr><th>Informação</th><th>Situação</th><th>Origem</th></tr></thead><tbody>
                  {e.gaps.map((gap) => <tr key={gap.gap_id}><td><strong>{gap.label_pt}</strong></td><td>{gap.explanation_pt}{gap.purpose_blocked.length > 0 && <div className="detail">Bloqueia: {gap.purpose_blocked.join(", ")}</div>}</td><td><small>{gap.origin === "SUGERIDA_POR_IA" ? "sugerida pela IA (não verificada)" : "curadoria"}</small></td></tr>)}
                </tbody></table>
              )}
            </div>
            {sel && <ReviewPanel key={sel.record_id} exp={e} param={sel} onChanged={exp.reload} onClose={() => setSelected(null)} />}
          </div>
        </>
      );
    }}</Async>
  );
}
