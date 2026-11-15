import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError, api } from "../api";
import { Async, Badge, ErrorBox, Term, useLoad } from "../components";
import { STATUS_LABEL, formatValue } from "../lib";

/** S05 — Alteração de parâmetros DO EXPERIMENTO (hipótese). Só condições de entrada elegíveis; nunca resultados observados. */
export default function Scenario() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const exp = useLoad(() => api.experiment(id), [id]);
  const compat = useLoad(() => api.compatibility(id), [id]);
  const [picked, setPicked] = useState<Record<string, string>>({});
  const [hypothesis, setHypothesis] = useState("");
  const [err, setErr] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);

  const invalid = useMemo(() => Object.entries(picked).some(([, v]) => v.trim() === "" || !Number.isFinite(Number(v))), [picked]);

  async function save() {
    setBusy(true); setErr(null);
    try {
      const sc = await api.createExperimentScenario(id, {
        changes: Object.entries(picked).map(([parameter, v]) => ({ parameter, value: Number(v) })),
        hypothesis: hypothesis || undefined, title: "Hipótese sobre " + (exp.data?.label ?? id),
      });
      nav(`/simulacao/${sc.scenario_id}`);
    } catch (e) { setErr(e as ApiError); setBusy(false); }
  }

  return (
    <Async state={exp}>{(e) => {
      const c = compat.data;
      const editable = c?.editable ?? [];
      const observed = e.parameters.filter((p) => p.role === "OBSERVAVEL");
      return (
        <>
          <div className="crumbs"><Link to="/">Experimentos NASA</Link> › <Link to={`/experimentos/${id}`}>{e.label}</Link> › Alterar parâmetros</div>
          <h1>Alterar parâmetros de {e.label}</h1>
          <p className="muted">Crie um cenário derivado: uma <Term k="hipotese">hipótese computacional</Term> sobre as condições deste experimento. O experimento original e seus valores <strong>não são alterados</strong>; somente as diferenças são registradas.</p>
          {c && !c.actions.simulate && <div className="box warn"><strong>Este experimento ainda não pode ser simulado no FDS.</strong> {c.reasons_pt.slice(0, 2).join(" ")} O cenário será salvo como hipótese, mas não será executado. Nenhuma simulação genérica será usada no lugar. {c.missing.length > 0 && <>Faltam: {c.missing.join(", ")}.</>}</div>}

          {editable.length === 0 ? (
            <div className="box bad">Este experimento não tem condições numéricas com unidade conhecida que possam ser alteradas. {c?.reasons_pt[0]}</div>
          ) : (
            <>
              <h2>Condições que podem ser alteradas</h2>
              <p className="muted">Marque o que deseja alterar. Cada campo mostra de onde vem o valor original, a unidade e a regra de validação.</p>
              {editable.map((p) => {
                const on = p.parameter in picked;
                const s = STATUS_LABEL[p.status] ?? { text: p.status, tone: "muted" as const };
                return (
                  <div className="card" key={p.parameter}>
                    <label className="row"><input type="checkbox" checked={on} onChange={(ev) => setPicked((st) => { const n = { ...st }; if (ev.target.checked) n[p.parameter] = String(p.value); else delete n[p.parameter]; return n; })} />
                      <strong>{p.label_pt}</strong> <Badge tone={s.tone}>{s.text}</Badge></label>
                    <p className="detail">Origem: {p.source_pt ?? "não informada"} · unidade: <strong>{p.unit}</strong> · regra: deve ser {p.rule_pt}.</p>
                    {on && (
                      <div className="compare">
                        <div><small className="muted">Original (preservado)</small><div><strong>{p.value} {p.unit}</strong></div></div><div>→</div>
                        <div><small className="muted">Novo valor ({p.unit})</small>
                          <div className="row"><input type="number" step="any" value={picked[p.parameter]} onChange={(ev) => setPicked((st) => ({ ...st, [p.parameter]: ev.target.value }))} aria-label={`Novo valor de ${p.label_pt}`} />
                            <button onClick={() => setPicked((st) => ({ ...st, [p.parameter]: String(p.value) }))}>Restaurar</button></div></div>
                      </div>
                    )}
                  </div>
                );
              })}
              <label className="wide">Hipótese (opcional)<br /><textarea rows={2} value={hypothesis} onChange={(ev) => setHypothesis(ev.target.value)} placeholder="O que você quer investigar com esta alteração?" /></label>
              {err && <ErrorBox error={err} />}
              <div className="row" style={{ marginTop: 10 }}>
                <button className="primary" disabled={busy || invalid || Object.keys(picked).length === 0} onClick={save}>Salvar cenário derivado</button>
                <Link className="btn" to={`/experimentos/${id}`}>Cancelar</Link>
              </div>
            </>
          )}

          <h2>Não editáveis</h2>
          <p className="detail"><Term k="observavel">Resultados observados</Term> são referência de comparação e nunca entradas de uma simulação; metadados e valores sem unidade conhecida também não são editáveis.</p>
          <table><tbody>{observed.map((p) => <tr key={p.record_id}><td>{p.label_pt}</td><td>{formatValue(p)}</td><td><Badge tone="muted">resultado observado</Badge></td></tr>)}</tbody></table>
        </>
      );
    }}</Async>
  );
}
