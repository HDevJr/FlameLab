import { useSearchParams } from "react-router-dom";
import { loadAllExperiments } from "../all_experiments";
import { Async, Badge, EmptyState, useLoad } from "../components";
import { compareExperiments, type Cell } from "../compare";

const ROLE = { CONDICAO: "Condições de entrada", OBSERVAVEL: "Resultados observados", METADADO: "Metadados" } as const;

const CellView = ({ c }: { c: Cell }) => !c ? <span className="muted">—</span> : (
  <div><strong>{c.text}</strong>{c.si != null && <div className="detail">SI: {Number(c.si.toPrecision(6))} {c.siUnit}</div>}
    <Badge tone={c.status === "CONFERIDO_FONTE" ? "ok" : "warn"}>{c.status === "CONFERIDO_FONTE" ? "conferido" : "não revisado"}</Badge>
    {c.page && <div className="detail">{c.page}</div>}</div>
);

/** Comparação lado a lado de dois experimentos do catálogo. Só valores registrados; nada é interpolado. */
export default function Compare() {
  const all = useLoad(loadAllExperiments, []);
  const [sp, setSp] = useSearchParams();
  return (
    <>
      <div className="crumbs">Comparar experimentos</div>
      <h1>Comparar experimentos</h1>
      <p className="muted">Parâmetros alinhados pelo nome técnico. Valores iguais em SI não aparecem como diferença; unidades incompatíveis não são comparadas numericamente.</p>
      <Async state={all}>{(list) => {
        if (list.length < 2) return <EmptyState title="São necessários pelo menos dois experimentos">Importe outro artigo para comparar com o BASS-II M1.</EmptyState>;
        const a = list.find((e) => e.experiment_id === sp.get("a")) ?? list[0];
        const b = list.find((e) => e.experiment_id === sp.get("b")) ?? list[1];
        const cmp = compareExperiments(a, b);
        const pick = (which: "a" | "b", v: string) => { const n = new URLSearchParams(sp); n.set("a", a.experiment_id); n.set("b", b.experiment_id); n.set(which, v); setSp(n); };
        return (
          <>
            <div className="compare-pick">
              {(["a", "b"] as const).map((w) => (
                <label key={w}>{w === "a" ? "Experimento A" : "Experimento B"}
                  <select value={(w === "a" ? a : b).experiment_id} onChange={(e) => pick(w, e.target.value)}>
                    {list.map((e) => <option key={e.experiment_id} value={e.experiment_id}>{e.label} — {e.document_title ?? e.document_id}</option>)}
                  </select></label>
              ))}
            </div>
            {cmp.warnings.map((w) => <div className="box warn" key={w}>{w}</div>)}
            <p><strong>{cmp.differing}</strong> parâmetros com valores diferentes · <strong>{cmp.onlyA}</strong> só em A · <strong>{cmp.onlyB}</strong> só em B</p>
            {(["CONDICAO", "OBSERVAVEL", "METADADO"] as const).map((role) => {
              const rows = cmp.rows.filter((r) => r.role === role);
              if (!rows.length) return null;
              return (
                <section key={role}><h2>{ROLE[role]}</h2>
                  <table className="cmp"><thead><tr><th>Parâmetro</th><th>{a.label}</th><th>{b.label}</th><th>Leitura</th></tr></thead><tbody>
                    {rows.map((r) => (
                      <tr key={r.key} className={r.differs ? "diff" : ""}>
                        <td data-l="Parâmetro"><strong>{r.label}</strong><div className="detail"><code>{r.key}</code></div></td>
                        <td data-l={a.label}><CellView c={r.a} /></td><td data-l={b.label}><CellView c={r.b} /></td>
                        <td data-l="Leitura">{r.note ? <span>{r.note}</span> : r.differs ? <Badge tone="warn">⚠ difere</Badge> : <Badge tone="ok">✔ igual</Badge>}</td>
                      </tr>))}
                  </tbody></table></section>
              );
            })}
          </>
        );
      }}</Async>
    </>
  );
}
