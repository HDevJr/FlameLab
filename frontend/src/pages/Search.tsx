import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { loadAllExperiments } from "../all_experiments";
import { Async, Badge, EmptyState, useLoad } from "../components";
import { searchExperiments } from "../search";

/** Busca textual simples sobre parâmetros e lacunas. A explicação de cada resultado mostra exatamente o que casou. */
export default function Search() {
  const all = useLoad(loadAllExperiments, []);
  const [q, setQ] = useState("");
  return (
    <>
      <div className="crumbs">Buscar</div>
      <h1>Buscar nos experimentos</h1>
      <p className="muted">Procura em nomes, valores, citações da fonte, ressalvas e lacunas. Ordenação por relevância para o texto digitado; não é avaliação de risco ou segurança.</p>
      <Async state={all}>{(list) => <Results list={list} q={q} setQ={setQ} />}</Async>
    </>
  );
}

function Results({ list, q, setQ }: { list: Parameters<typeof searchExperiments>[0]; q: string; setQ: (s: string) => void }) {
  const hits = useMemo(() => searchExperiments(list, q), [list, q]);
  return (
    <>
      <label className="sr-only" htmlFor="q">Texto da busca</label>
      <input id="q" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ex.: pressão, temperatura, 22,2" style={{ width: "100%", maxWidth: 520 }} />
      <p className="detail">{list.length} experimentos indexados.</p>
      {!q.trim() && <EmptyState title="Digite um termo">Tente “pressão”, “oxigênio” ou o nome de um parâmetro.</EmptyState>}
      {q.trim() && hits.length === 0 && <EmptyState title="Nenhum resultado">Nada nos parâmetros e lacunas dos experimentos carregados casa com “{q}”.</EmptyState>}
      <ul className="hits">{hits.slice(0, 50).map((h) => (
        <li key={h.id} className="card">
          <div className="row"><Badge tone={h.kind === "Lacuna" ? "warn" : "info"}>{h.kind}</Badge><strong className="grow"><Link to={h.to}>{h.title}</Link></strong><small className="muted">{h.experiment} · relevância {h.score}</small></div>
          <div className="detail">{h.snippet}</div>
          <details className="tech"><summary>Por que apareceu</summary><ul>{h.why.map((w) => <li key={w}>{w}</li>)}</ul></details>
        </li>))}</ul>
      {hits.length > 50 && <p className="detail">Mostrando os 50 mais relevantes de {hits.length}.</p>}
    </>
  );
}
