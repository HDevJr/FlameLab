import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError, api, type SimModel } from "../api";
import { Async, Badge, DataKind, ErrorBox, useLoad } from "../components";
import { formatValue, validateChange } from "../lib";

/** S05 — Alteração de parâmetros. O formulário é gerado a partir do modelo; só aparecem campos editáveis. */
export default function Scenario() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const exp = useLoad(() => api.experiment(id), [id]);
  const models = useLoad(api.models, []);
  const [picked, setPicked] = useState<Record<string, string>>({}); // nome → texto digitado (presente = alterar)
  const [err, setErr] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);

  const model: SimModel | undefined = useMemo(() => models.data?.find((m) => m.implemented), [models.data]);

  const errors = useMemo(() => {
    const out: Record<string, string | null> = {};
    for (const p of model?.parameters ?? []) if (p.name in picked) out[p.name] = validateChange(Number(picked[p.name]), p.min, p.max, p.unit);
    return out;
  }, [picked, model]);
  const hasErrors = Object.values(errors).some(Boolean);

  async function save(changed: boolean) {
    if (!model) return;
    setBusy(true); setErr(null);
    try {
      const values = changed ? Object.fromEntries(Object.entries(picked).map(([k, v]) => [k, Number(v)])) : {};
      const sc = await api.createScenario({ model_id: model.model_id, values, experiment_id: id, title: changed ? "Cenário derivado" : "Caso-base" });
      nav(`/simulacao/${sc.scenario_id}`);
    } catch (e) { setErr(e as ApiError); setBusy(false); }
  }

  return (
    <Async state={exp}>{(e) => (
      <>
        <div className="crumbs"><Link to="/">Biblioteca</Link> › <Link to={`/experimentos/${id}`}>{e.label}</Link> › Alterar parâmetros</div>
        <h1>Alterar parâmetros</h1>
        <div className="card">
          <h3>Caso-base: {e.label}</h3>
          <p className="detail">Valores do experimento (somente leitura; o original nunca é alterado):</p>
          <table><tbody>{e.parameters.filter((p) => p.role === "CONDICAO").map((p) => <tr key={p.record_id}><td>{p.label_pt}</td><td>{formatValue(p)}</td></tr>)}</tbody></table>
        </div>
        <div className="box warn">
          Este experimento ainda não tem um modelo de reprodução FDS (lacunas científicas e gerador não implementado). Os campos abaixo pertencem ao <strong>caso de integração do pipeline</strong> — um queimador genérico — e não representam o experimento acima.
        </div>
        <Async state={models}>{() => !model ? <p className="muted">Nenhum modelo executável disponível.</p> : (
          <>
            <div className="row"><h2 className="grow">{model.title_pt}</h2><DataKind kind="TESTE" /></div>
            <p className="muted">{model.description_pt}</p>
            <p className="detail">Origem do caso-base: {model.template_source?.origin}</p>
            <h3>Selecione o que deseja modificar</h3>
            {model.parameters.map((p) => {
              const on = p.name in picked;
              return (
                <div className="card" key={p.name}>
                  <label className="row"><input type="checkbox" checked={on} onChange={(ev) => setPicked((s) => { const n = { ...s }; if (ev.target.checked) n[p.name] = String(p.default); else delete n[p.name]; return n; })} />
                    <strong>{p.label_pt}</strong> <Badge tone={p.group === "HIPOTESE" ? "warn" : "muted"}>{p.group === "HIPOTESE" ? "hipótese" : p.group === "NUMERICO" ? "numérico" : "contorno"}</Badge></label>
                  {p.help_pt && <p className="detail">{p.help_pt} Faixa permitida: {p.min} a {p.max} {p.unit}.</p>}
                  {on && (
                    <div className="compare">
                      <div><small className="muted">Original</small><div><strong>{p.default} {p.unit}</strong></div></div><div>→</div>
                      <div><small className="muted">Novo</small><div className="row"><input type="number" step={p.step ?? "any"} value={picked[p.name]} onChange={(ev) => setPicked((s) => ({ ...s, [p.name]: ev.target.value }))} /> {p.unit}
                        <button onClick={() => setPicked((s) => ({ ...s, [p.name]: String(p.default) }))}>Restaurar</button></div>
                        {errors[p.name] && <div className="detail" style={{ color: "var(--bad)" }}>{errors[p.name]}</div>}</div>
                    </div>
                  )}
                </div>
              );
            })}
            {err && <ErrorBox error={err} />}
            <div className="row">
              <button className="primary" disabled={busy || hasErrors || Object.keys(picked).length === 0} onClick={() => save(true)}>Salvar cenário derivado</button>
              <button disabled={busy} onClick={() => save(false)}>Usar o caso-base sem alterações</button>
            </div>
            <p className="detail">Um cenário derivado é uma <strong>hipótese computacional</strong>. Apenas as alterações são registradas; o caso-base é preservado.</p>
          </>
        )}</Async>
      </>
    )}</Async>
  );
}
