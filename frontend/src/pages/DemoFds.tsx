import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError, api, type SimModel } from "../api";
import { Async, Badge, DataKind, ErrorBox, Term, useLoad } from "../components";
import { validateChange } from "../lib";

/** Demonstração FDS — caso genérico e INDEPENDENTE de qualquer artigo. Prova o pipeline FDS → Smokeview → vídeo. */
export default function DemoFds() {
  const nav = useNavigate();
  const models = useLoad(api.models, []);
  const [picked, setPicked] = useState<Record<string, string>>({});
  const [err, setErr] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const model: SimModel | undefined = useMemo(() => models.data?.find((m) => m.implemented && m.purpose === "INTEGRATION_TEST"), [models.data]);

  const errors = useMemo(() => {
    const out: Record<string, string | null> = {};
    for (const p of model?.parameters ?? []) if (p.name in picked) out[p.name] = validateChange(Number(picked[p.name]), p.min, p.max, p.unit);
    return out;
  }, [picked, model]);

  async function save(changed: boolean) {
    if (!model) return;
    setBusy(true); setErr(null);
    try {
      const values = changed ? Object.fromEntries(Object.entries(picked).map(([k, v]) => [k, Number(v)])) : {};
      const sc = await api.createScenario({ model_id: model.model_id, values, title: changed ? "Demonstração derivada" : "Demonstração (caso-base)" });
      nav(`/simulacao/${sc.scenario_id}`);
    } catch (e) { setErr(e as ApiError); setBusy(false); }
  }

  return (
    <>
      <div className="row"><h1 className="grow">Demonstração FDS</h1><DataKind kind="TESTE" /></div>
      <Link className="btn" to="/preparar-simulacao">Preparar caso rastreável em quatro etapas</Link>
      <div className="box warn">
        <strong>Isto não é um experimento NASA.</strong> Este é um caso genérico — um queimador de propano em uma sala — criado só para provar que o FlameLab consegue gerar, executar e renderizar um caso <Term k="fds">FDS</Term>. Os parâmetros abaixo <strong>não pertencem a nenhum artigo</strong> (nem ao BASS-II) e os resultados não têm relação com dados da NASA. Para trabalhar com um artigo, use <Link to="/">Experimentos NASA</Link>.
      </div>
      <Async state={models}>{() => !model ? <p className="muted">Nenhum modelo executável disponível.</p> : (
        <>
          <h2>{model.title_pt}</h2>
          <p className="muted">{model.description_pt}</p>
          <p className="detail">Origem do caso-base: {model.template_source?.origin}. Os quadros do vídeo são as saídas do FDS a cada 0,1 s simulado, sem interpolação.</p>
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
            <button className="primary" disabled={busy || Object.values(errors).some(Boolean) || Object.keys(picked).length === 0} onClick={() => save(true)}>Salvar cenário derivado da demonstração</button>
            <button disabled={busy} onClick={() => save(false)}>Usar o caso-base sem alterações</button>
          </div>
          <p className="detail">O cenário derivado é uma <strong>hipótese computacional</strong>; o caso-base é preservado.</p>
        </>
      )}</Async>
    </>
  );
}
