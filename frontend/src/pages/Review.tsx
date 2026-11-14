import { Link, useParams } from "react-router-dom";
import { api, type Experiment, type Parameter } from "../api";
import { Async, Badge, DataKind, useLoad } from "../components";
import { COMPAT_LABEL, STATUS_LABEL, formatValue, groupByRole } from "../lib";

function ParamTable({ rows, title, hint }: { rows: Parameter[]; title: string; hint: string }) {
  if (!rows.length) return null;
  return (
    <>
      <h2>{title}</h2><p className="muted">{hint}</p>
      <table><thead><tr><th>Parâmetro</th><th>Valor (original)</th><th>Estado</th><th>Origem</th></tr></thead><tbody>
        {rows.map((p) => {
          const s = STATUS_LABEL[p.status] ?? { text: p.status, tone: "muted" as const };
          return (
            <tr key={p.record_id}>
              <td><strong>{p.label_pt}</strong><div className="detail">{p.nature}</div></td>
              <td>{formatValue(p)}{p.normalized && <div className="detail">SI: {p.normalized.value} {p.normalized.unit}</div>}</td>
              <td><Badge tone={s.tone}>{s.text}</Badge>{p.extraction && <div className="detail">{p.extraction.method}</div>}</td>
              <td>{p.evidence.map((e, i) => <div key={i}><small>{e.locator_pt || (e.page_pdf ? `PDF p. ${e.page_pdf}` : "—")}</small>{e.quote && <div className="detail">“{e.quote.slice(0, 140)}”</div>}</div>)}
                {p.caveats_pt.map((c) => <div className="detail" key={c}>⚠ {c}</div>)}</td>
            </tr>
          );
        })}
      </tbody></table>
    </>
  );
}

/** S04 — Revisão dos parâmetros: condições separadas de resultados observados + prontidão para o FDS. */
export default function Review() {
  const { id = "" } = useParams();
  const exp = useLoad<Experiment>(() => api.experiment(id), [id]);
  const compat = useLoad(() => api.compatibility(id), [id]);
  return (
    <Async state={exp}>{(e) => {
      const g = groupByRole(e.parameters);
      const c = compat.data;
      const label = c ? COMPAT_LABEL[c.status] : null;
      return (
        <>
          <div className="crumbs"><Link to="/">Biblioteca</Link> › {e.document_title ?? e.document_id} › {e.label}</div>
          <div className="row"><h1 className="grow">{e.label}</h1><DataKind kind={e.review.reviewed === e.review.total && e.review.total > 0 ? "REAL" : "REVISAO"} /></div>
          {e.description && <p className="muted">{e.description}</p>}
          <p><strong>{e.review.reviewed}</strong> de <strong>{e.review.total}</strong> parâmetros conferidos por humano · <strong>{e.review.gaps}</strong> lacunas registradas.
            {e.review.reviewed < e.review.total && " Valores não revisados não devem ser citados como dados da fonte."}</p>

          <div className="card">
            <div className="row"><h3 style={{ margin: 0 }}>Prontidão para simulação (FDS)</h3>{label && <Badge tone={label.tone}>{label.text}</Badge>}</div>
            {c ? <ul>{c.reasons_pt.map((r) => <li key={r}>{r}</li>)}</ul> : <p className="muted">Avaliando…</p>}
            {c && c.missing.length > 0 && <p className="detail">Faltando para o modelo: {c.missing.join(", ")}</p>}
            <div className="row">
              <button className="primary" disabled={!c?.actions.simulate} title={c?.actions.simulate ? "" : "Indisponível: veja os motivos acima"}>Iniciar simulação</button>
              <Link className={`btn ${c?.actions.alter ? "" : "disabled"}`} to={`/experimentos/${id}/alterar`}>Alterar parâmetros</Link>
              <Link className="btn" to={`/documentos/${e.document_id}/enriquecimento`}>Consultar fontes</Link>
            </div>
            <p className="detail">Mesmo sem compatibilidade, análise, comparação de fontes e exportação seguem disponíveis. “Alterar parâmetros” abre o caso de integração do pipeline, que não reproduz este experimento.</p>
          </div>

          <ParamTable rows={g.conditions} title="Condições experimentais" hint="Entradas do experimento, como descritas na fonte." />
          <ParamTable rows={g.observed} title="Resultados observados" hint="Medições do experimento. São referência de comparação, nunca entradas da simulação." />
          <ParamTable rows={g.metadata} title="Metadados" hint="Identificação do material, do equipamento ou do contexto." />

          <h2>Campos ausentes ({e.gaps.length})</h2>
          {e.gaps.length === 0 ? <p className="muted">Nenhuma lacuna registrada.</p> : (
            <table><thead><tr><th>Informação</th><th>Situação</th><th>Origem</th></tr></thead><tbody>
              {e.gaps.map((gap) => <tr key={gap.gap_id}><td><strong>{gap.label_pt}</strong></td><td>{gap.explanation_pt}{gap.purpose_blocked.length > 0 && <div className="detail">Bloqueia: {gap.purpose_blocked.join(", ")}</div>}</td><td><small>{gap.origin === "SUGERIDA_POR_IA" ? "sugerida pela IA (não verificada)" : "curadoria"}</small></td></tr>)}
            </tbody></table>
          )}
        </>
      );
    }}</Async>
  );
}
